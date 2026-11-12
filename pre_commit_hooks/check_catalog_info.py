from __future__ import annotations

import contextlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from fnmatch import fnmatch
from itertools import takewhile

import click
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from pre_commit_hooks.util import project_dir

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # ty: ignore[unresolved-import]

CATALOG = "catalog-info.yaml"
HEADER = "# yaml-language-server: $schema=https://json.schemastore.org/catalog-info.json"
ANNOTATION = "endoflife.date/products"
EOL_KINDS = ("Component", "Resource")

API = "https://endoflife.date/api/v1/products/{}/"
PRODUCT = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
VERSION = re.compile(r"\d+(?:\.\d+)*")
BAD_PAYLOAD = (ValueError, KeyError, TypeError)  # malformed JSON or unexpected shape
# mise / asdf tool name -> endoflife.date product
TOOL_ALIASES = {"node": "nodejs", "java": "eclipse-temurin", "maven": "apache-maven"}


class UnknownProduct(Exception):
    pass


# --- endoflife.date API ------------------------------------------------------


def cache_dir() -> str:
    return os.path.join(tempfile.gettempdir(), "pre-commit-hooks-endoflife")


def cache_usable() -> bool:
    """The cache dir is a real directory owned by us (shared $TMPDIR: others must not plant files)."""
    try:
        os.makedirs(cache_dir(), mode=0o700, exist_ok=True)
        st = os.lstat(cache_dir())
    except OSError:
        return False
    return stat.S_ISDIR(st.st_mode) and (not hasattr(os, "getuid") or st.st_uid == os.getuid())


def write_cache(path: str, data: bytes) -> None:
    """Atomic best-effort write: a failing cache must not lose the fetched result."""
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache_dir(), delete=False) as f:
            tmp = f.name
            f.write(data)
        os.replace(tmp, path)
    except OSError:
        if tmp:
            with contextlib.suppress(OSError):
                os.remove(tmp)


# product -> fetch error, for the rest of this run
FETCH_FAILED: dict[str, OSError] = {}


def releases(product: str, ttl: int, offline: bool = False) -> list[dict] | None:
    """Releases of `product`, newest first.

    A cache file younger than `ttl` is used as is; an older one only when the fetch fails.
    Offline: any cache file, or None when there is none.
    """
    if not PRODUCT.match(product):  # the name ends up in a URL and a file path
        raise UnknownProduct(product)
    path = os.path.join(cache_dir(), f"{product}.json")
    usable = cache_usable()
    cached = None
    try:
        if not usable:
            raise OSError
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)["result"]["releases"]
        if offline or time.time() - os.path.getmtime(path) < ttl:
            return cached
    except (OSError, *BAD_PAYLOAD):
        pass  # missing or broken cache entry: refetch
    if offline:
        return cached
    try:
        if product in FETCH_FAILED:  # don't wait out the timeout again for every entity
            raise FETCH_FAILED[product]
        with urllib.request.urlopen(API.format(product), timeout=30) as r:
            data = r.read()
    except OSError as e:  # HTTPError and URLError are OSErrors
        FETCH_FAILED[product] = e
        if getattr(e, "code", None) == 404:
            raise UnknownProduct(product) from None
        if cached is not None:
            return cached  # stale beats nothing
        raise
    result = json.loads(data)["result"]["releases"]
    if usable:
        write_cache(path, data)
    return result


def api_error(product: str, e: Exception) -> str:
    if isinstance(e, UnknownProduct):
        return f"{product}: unknown endoflife.date product"
    if isinstance(e, OSError):
        return f"{product}: endoflife.date API unreachable ({e}), use --offline"
    return f"{product}: bad endoflife.date API response ({e!r})"


def lowest(pin: str) -> str | None:
    """Lowest version in a pin or constraint: `>=3.10,<4` -> `3.10`, `latest` -> None."""
    # ponytail: first number, not the true lower bound (`<4,>=3.10` -> `4`); parse specifiers if that bites
    m = VERSION.search(pin)
    return m.group() if m else None


def to_cycle(version: str, cycles: list[str] | None) -> str:
    """Longest known cycle that `version` belongs to; `major.minor` when offline or unknown."""
    for c in sorted(cycles or (), key=len, reverse=True):
        if version == c or version.startswith(c + "."):
            return c
    return ".".join(version.split(".")[:2])


def latest(rels: list[dict]) -> str:
    """Newest non-EOL cycle, or the newest one if all are EOL."""
    return next((r["name"] for r in rels if not r.get("isEol")), rels[0]["name"])


# --- detection ---------------------------------------------------------------


def repo_files(root: str) -> list[str]:
    out = subprocess.run(
        ("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"),
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split("\0")[:-1]  # -z: NUL-terminated, paths stay unquoted


def read(root: str, name: str) -> str | None:
    try:
        with open(os.path.join(root, name), encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError):  # ValueError: UnicodeDecodeError
        return None


def first_line(root: str, name: str) -> str | None:
    text = read(root, name)
    return text.strip().splitlines()[0] if text and text.strip() else None


def load_json(root: str, name: str) -> dict:
    try:
        data = json.loads(read(root, name) or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def load_toml(root: str, name: str) -> dict:
    try:
        return tomllib.loads(read(root, name) or "")
    except tomllib.TOMLDecodeError:
        return {}


def search(pattern: str, text: str | None) -> str | None:
    m = re.search(pattern, text or "", re.MULTILINE)
    return m.group(1) if m else None


def dig(data: object, *keys: str) -> str | None:
    """`data[k1][k2]...` when every level is a dict and the leaf is a string, else None."""
    for key in keys:
        data = data.get(key) if isinstance(data, dict) else None
    return data if isinstance(data, str) else None


def tool_pins(root: str) -> dict[str, str]:
    """Versions pinned in mise.toml / .mise.toml / .tool-versions, keyed by product."""
    pins: dict[str, str] = {}
    for line in (read(root, ".tool-versions") or "").splitlines():
        parts = line.split("#")[0].split()
        if len(parts) >= 2:
            pins[parts[0]] = parts[1]
    for name in (".mise.toml", "mise.toml"):  # mise.toml wins
        tools = load_toml(root, name).get("tools")
        if not isinstance(tools, dict):
            continue
        for tool, value in tools.items():
            if isinstance(value, list):
                value = value[0] if value else ""
            if isinstance(value, dict):
                value = value.get("version", "")
            if isinstance(value, str):
                pins[tool] = value
    return {TOOL_ALIASES.get(tool, tool): pin for tool, pin in pins.items()}


def detect(root: str, files: list[str]) -> dict[str, str | None]:
    """Products used in the repo -> their pinned version (None when unpinned)."""
    names = {os.path.basename(f) for f in files}

    def has(*patterns: str) -> bool:
        return any(fnmatch(n, p) for n in names for p in patterns)

    package = load_json(root, "package.json")
    manager = dig(package, "packageManager") or ""
    tf = "\n".join(read(root, f) or "" for f in files if f.endswith(".tf"))
    tools = tool_pins(root)
    found: dict[str, str | None] = {}

    if has("*.py", "pyproject.toml"):
        found["python"] = first_line(root, ".python-version") or dig(
            load_toml(root, "pyproject.toml"), "project", "requires-python"
        )
    if "package.json" in names:
        found["nodejs"] = (
            first_line(root, ".nvmrc") or first_line(root, ".node-version") or dig(package, "engines", "node")
        )
    for product, lockfiles in (
        ("pnpm", ("pnpm-lock.yaml",)),
        ("yarn", ("yarn.lock",)),
        ("bun", ("bun.lock", "bun.lockb")),
    ):
        if has(*lockfiles):
            found[product] = manager.partition("@")[2] if manager.startswith(product + "@") else None
    if has("deno.json", "deno.jsonc"):
        found["deno"] = None
    if "go.mod" in names:
        found["go"] = search(r"^go\s+(\S+)", read(root, "go.mod"))
    if has("composer.json", "*.php"):
        found["php"] = dig(load_json(root, "composer.json"), "require", "php")
        found["composer"] = None
    if "pom.xml" in names:
        found["eclipse-temurin"] = search(r"<maven\.compiler\.release>\s*(\d+)", read(root, "pom.xml"))
        found["apache-maven"] = None
    if has("build.gradle", "build.gradle.kts"):
        gradle = (read(root, "build.gradle") or "") + (read(root, "build.gradle.kts") or "")
        found["eclipse-temurin"] = search(r"JavaLanguageVersion\.of\((\d+)\)", gradle)
        found["gradle"] = search(
            r"gradle-(\d+(?:\.\d+)*)-",
            read(root, os.path.join("gradle", "wrapper", "gradle-wrapper.properties")),
        )
    if has("*.tf"):
        tofu = ".opentofu-version" in names or "opentofu" in tools
        found["opentofu" if tofu else "terraform"] = (
            first_line(root, ".opentofu-version") if tofu else None
        ) or search(r'^\s*required_version\s*=\s*"([^"]+)"', tf)
    if "Gemfile" in names:
        found["ruby"] = first_line(root, ".ruby-version")
    if "Cargo.toml" in names:
        found["rust"] = dig(load_toml(root, "rust-toolchain.toml"), "toolchain", "channel")

    for product in found:
        if lowest(tools.get(product, "")):  # exact mise/asdf pin beats a range like `>= 1.11`
            found[product] = tools[product]
    return found


# --- catalog-info.yaml editing -----------------------------------------------


def split_prelude(text: str) -> tuple[str, str]:
    """Leading comment and blank lines (ruamel drops comments before `---`) and the rest."""
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith("#") or not lines[i].strip()):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:])


def yaml_rt() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # never re-wrap long or folded scalars
    return y


def parse_products(value: object) -> dict[str, str]:
    """`python@3.12, nodejs@20` -> {"python": "3.12", "nodejs": "20"}."""
    out: dict[str, str] = {}
    for item in str(value or "").split(","):
        product, _, cycle = item.strip().partition("@")
        if product:
            out[product.strip()] = cycle.strip()
    return out


def resolve(
    detected: dict[str, str | None], offline: bool, ttl: int, errors: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Detected products -> (cycles from repo pins, newest cycles for unpinned products)."""
    pinned: dict[str, str] = {}
    fallback: dict[str, str] = {}
    for product, pin in sorted(detected.items()):
        version = lowest(pin) if pin else None
        try:
            rels = releases(product, ttl, offline)
        except (UnknownProduct, OSError, *BAD_PAYLOAD) as e:
            errors.append(api_error(product, e))
            continue
        if version and rels is None:  # offline, nothing cached: a guess may fill a gap, never overwrite
            fallback[product] = to_cycle(version, None)
        elif version and rels is not None:
            pinned[product] = to_cycle(version, [r["name"] for r in rels])
        elif rels:
            fallback[product] = latest(rels)
        elif offline:
            click.echo(f"{CATALOG}: {product}: no version pinned and nothing cached, skipped (--offline)")
    return pinned, fallback


def merge(
    existing: dict[str, str], pinned: dict[str, str], fallback: dict[str, str], fixes: list[str]
) -> dict[str, str]:
    products = dict(existing)
    for product, cycle in fallback.items():
        if product not in products:
            products[product] = cycle
            fixes.append(f"added {product}@{cycle} to {ANNOTATION}")
    for product, cycle in pinned.items():
        if product not in products:
            fixes.append(f"added {product}@{cycle} to {ANNOTATION}")
        elif products[product] != cycle:
            fixes.append(f"updated {product}@{products[product]} to {product}@{cycle} (repo pin)")
        products[product] = cycle
    return dict(sorted(products.items()))


def check_cycles(products: dict[str, str], offline: bool, ttl: int, errors: list[str]) -> None:
    for product, cycle in products.items():
        if not cycle:
            errors.append(f"{product}: missing @cycle in {ANNOTATION}")
            continue
        try:
            rels = releases(product, ttl, offline)
        except (UnknownProduct, OSError, *BAD_PAYLOAD) as e:
            errors.append(api_error(product, e))
            continue
        if rels is not None and cycle not in [r["name"] for r in rels]:  # None: offline, nothing cached
            errors.append(f"{product}@{cycle}: unknown cycle, see {API.format(product)}")


def set_annotation(meta: CommentedMap, value: str) -> None:
    annotations = meta.get("annotations")
    if annotations is None:
        keys = list(meta)
        after = max(keys.index(k) for k in ("name", "namespace", "title", "description") if k in keys)
        meta.insert(after + 1, "annotations", {ANNOTATION: value})
    else:
        annotations[ANNOTATION] = value


@click.command()
@click.option("--offline", is_flag=True, help="Do not call the endoflife.date API.")
@click.option(
    "--cache-ttl",
    type=int,
    default=86400,
    show_default=True,
    help="Seconds an endoflife.date API response stays cached.",
)
def main(offline: bool, cache_ttl: int) -> int:
    """Checks and fixes the repo's Backstage catalog-info.yaml."""
    root = project_dir()
    path = os.path.join(root, CATALOG)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        click.echo(f"{CATALOG}: not found in {root}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        click.echo(f"{CATALOG}: not valid UTF-8 ({e})")
        sys.exit(1)

    fixes: list[str] = []
    errors: list[str] = []
    prelude, body = split_prelude(text)
    if not any(
        "yaml-language-server:" in line for line in takewhile(lambda line: line.startswith("#"), prelude.splitlines())
    ):
        prelude = HEADER + "\n" + prelude
        fixes.append("added yaml-language-server header")

    y = yaml_rt()
    y.explicit_start = body.lstrip().startswith("---")
    try:
        docs = list(y.load_all(body))
    except YAMLError as e:
        click.echo(f"{CATALOG}: {e}")
        sys.exit(1)
    if all(doc is None for doc in docs):
        click.echo(f"{CATALOG}: no entities")
        sys.exit(1)

    resolved = None
    dirty = False  # body re-dumped only when an entity changed, so valid files stay byte-identical
    for i, doc in enumerate(docs):
        if doc is None:  # empty document, e.g. a trailing `---`
            continue
        meta = doc.get("metadata") if isinstance(doc, dict) else None
        if not isinstance(meta, dict) or not meta.get("name"):
            errors.append(f"document {i}: metadata.name is required")
            continue
        if "namespace" not in meta:
            meta.insert(list(meta).index("name") + 1, "namespace", "default")
            fixes.append(f"{meta['name']}: added metadata.namespace: default")
            dirty = True
        if doc.get("kind") not in EOL_KINDS:
            continue
        if resolved is None:  # detection and API lookups only when an entity needs them
            resolved = resolve(detect(root, repo_files(root)), offline, cache_ttl, errors)
        annotations = meta.get("annotations")
        if annotations is not None and not isinstance(annotations, dict):
            errors.append(f"{meta['name']}: metadata.annotations must be a mapping")
            continue
        current = (annotations or {}).get(ANNOTATION)
        fixes_before, errors_before = len(fixes), len(errors)
        products = merge(parse_products(current), *resolved, fixes)
        check_cycles(products, offline, cache_ttl, errors)
        if len(errors) > errors_before:  # never write an annotation we know is invalid
            del fixes[fixes_before:]
            continue
        value = ",".join(f"{p}@{c}" for p, c in products.items())
        if value and value != current:
            if len(fixes) == fixes_before:
                fixes.append(f"normalized {ANNOTATION}")
            fixes[fixes_before:] = [f"{meta['name']}: {fix}" for fix in fixes[fixes_before:]]
            set_annotation(meta, value)
            dirty = True

    if dirty:
        out = io.StringIO()
        y.dump_all([doc for doc in docs if doc is not None], out)  # ruamel writes empty docs as `...`
        body = out.getvalue()
    if fixes:
        with open(path, "w", encoding="utf-8") as f:
            f.write(prelude + body)
    for message in fixes + errors:
        click.echo(f"{CATALOG}: {message}")
    sys.exit(1 if fixes or errors else 0)


if __name__ == "__main__":
    main()
