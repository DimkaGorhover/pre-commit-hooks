from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from email.message import Message

import pytest
from click.testing import CliRunner

from pre_commit_hooks import check_catalog_info as cci
from pre_commit_hooks.check_catalog_info import main

HEADER = "# yaml-language-server: $schema=https://json.schemastore.org/catalog-info.json\n"
CYCLES = {
    "python": ["3.14", "3.13", "3.12", "3.11", "3.10"],
    "nodejs": ["26", "24", "22", "20"],
    "pnpm": ["10", "9"],
    "go": ["1.25", "1.24"],
    "php": ["8.5", "8.4", "8.3"],
    "composer": ["2.8", "2.2"],
    "terraform": ["1.16", "1.15"],
    "gitlab": ["19.3", "19.2"],
}
COMPONENT = """\
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: svc
  namespace: default
spec:
  type: service
"""


def seed(product: str, cycles: list[str], eol: tuple[str, ...] = ()) -> str:
    os.makedirs(cci.cache_dir(), exist_ok=True)
    path = os.path.join(cci.cache_dir(), f"{product}.json")
    releases = [{"name": c, "isEol": c in eol} for c in cycles]
    with open(path, "w") as f:
        json.dump({"result": {"releases": releases}}, f)
    return path


def newest(product: str, ttl: int, offline: bool = False) -> str:
    rels = cci.releases(product, ttl, offline)
    assert rels is not None
    return rels[0]["name"]


def serve_body(monkeypatch, body: bytes) -> None:
    """Fake API answering every product with `body`."""

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body

    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout: Response())


def serve(monkeypatch, cycles: list[str]) -> None:
    serve_body(
        monkeypatch, json.dumps({"result": {"releases": [{"name": c, "isEol": False} for c in cycles]}}).encode()
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    subprocess.run(("git", "init", "-q", str(root)), check=True)
    monkeypatch.chdir(root)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))  # cache dir outside the repo

    def no_network(*args, **kwargs):
        raise AssertionError("network access in tests")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    for product, cycles in CYCLES.items():
        seed(product, cycles)
    return root


def write(root, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def run(*args: str):
    return CliRunner().invoke(main, args)


def catalog(root) -> str:
    return (root / "catalog-info.yaml").read_text()


def test_missing_file(repo):
    result = run()
    assert result.exit_code == 1
    assert "not found" in result.output


def test_valid_file_unchanged(repo):
    text = HEADER + "# nonk8s\n" + COMPONENT
    write(repo, {"catalog-info.yaml": text})
    assert run().exit_code == 0
    assert catalog(repo) == text


def test_adds_header(repo):
    write(repo, {"catalog-info.yaml": "# nonk8s\n" + COMPONENT})
    assert run().exit_code == 1
    assert catalog(repo) == HEADER + "# nonk8s\n" + COMPONENT


def test_keeps_other_schema_header(repo):
    text = "# yaml-language-server: $schema=./my.json\n" + COMPONENT
    write(repo, {"catalog-info.yaml": text})
    assert run().exit_code == 0
    assert catalog(repo) == text


def test_adds_namespace_to_every_document(repo):
    text = (
        HEADER
        + COMPONENT.replace("  namespace: default\n", "")
        + (
            "---\napiVersion: backstage.io/v1alpha1\nkind: Location\nmetadata:\n"
            "  name: loc\nspec:\n  targets:\n    - ./*/catalog-info.yaml\n"
        )
    )
    write(repo, {"catalog-info.yaml": text})
    assert run().exit_code == 1
    out = catalog(repo)
    assert "  name: svc\n  namespace: default\n" in out
    assert "  name: loc\n  namespace: default\n" in out
    assert "    - ./*/catalog-info.yaml\n" in out
    assert run().exit_code == 0  # idempotent


def test_missing_name(repo):
    write(repo, {"catalog-info.yaml": HEADER + "---\nkind: Location\nmetadata: {}\n"})
    result = run()
    assert result.exit_code == 1
    assert "document 0: metadata.name is required" in result.output


def test_invalid_yaml(repo):
    write(repo, {"catalog-info.yaml": HEADER + "metadata: [x\n"})
    assert run().exit_code == 1


def test_empty_file(repo):
    write(repo, {"catalog-info.yaml": HEADER})
    result = run()
    assert result.exit_code == 1
    assert "no entities" in result.output


def test_trailing_document_separator(repo):
    text = HEADER + COMPONENT + "---\n"
    write(repo, {"catalog-info.yaml": text})
    assert run().exit_code == 0
    write(repo, {"catalog-info.yaml": text.replace("  namespace: default\n", "")})
    assert run().exit_code == 1
    assert catalog(repo) == text.removesuffix("---\n")  # empty documents are dropped on rewrite


def test_prelude_keeps_comments_after_blank_line(repo):
    write(repo, {"catalog-info.yaml": "# nonk8s\n\n# keep me\n" + COMPONENT.replace("  namespace: default\n", "")})
    assert run().exit_code == 1
    assert catalog(repo) == HEADER + "# nonk8s\n\n# keep me\n" + COMPONENT


def test_header_must_be_in_first_comment_block(repo):
    text = "# nonk8s\n\n# yaml-language-server: $schema=./my.json\n" + COMPONENT
    write(repo, {"catalog-info.yaml": text})
    assert run().exit_code == 1
    assert catalog(repo) == HEADER + text


def test_releases_uses_fresh_cache(repo):
    assert newest("gitlab", 1000) == "19.3"  # urlopen would raise


def test_releases_refetches_stale_entry(repo, monkeypatch):
    path = seed("gitlab", ["19.2"])
    os.utime(path, (time.time() - 100, time.time() - 100))
    serve(monkeypatch, ["19.3"])
    assert newest("gitlab", 1000) == "19.2"  # still fresh
    assert newest("gitlab", 10) == "19.3"  # stale: refetched
    with open(path) as f:
        assert json.load(f)["result"]["releases"][0]["name"] == "19.3"


def test_releases_rejects_bad_name(repo):
    with pytest.raises(cci.UnknownProduct):
        cci.releases("../../etc/passwd", 1000)


def test_releases_404(repo, monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", Message(), None)

    monkeypatch.setattr(urllib.request, "urlopen", not_found)
    with pytest.raises(cci.UnknownProduct):
        cci.releases("nope", 1000)


def test_latest():
    assert cci.latest([{"name": "3", "isEol": True}, {"name": "2", "isEol": False}]) == "2"
    assert cci.latest([{"name": "3", "isEol": True}]) == "3"


@pytest.mark.parametrize(
    ("version", "cycles", "expected"),
    (
        ("3.12.4", ["3.13", "3.12"], "3.12"),
        ("20.11.0", ["22", "20"], "20"),
        ("20.1", ["2"], "20.1"),
        ("1.16.0", None, "1.16"),
        ("21", None, "21"),
    ),
)
def test_to_cycle(version, cycles, expected):
    assert cci.to_cycle(version, cycles) == expected


@pytest.mark.parametrize(
    ("pin", "expected"),
    (
        (">=3.10,<4", "3.10"),
        ("^3.12", "3.12"),
        ("~> 1.16.0", "1.16.0"),
        ("v20.11.0", "20.11.0"),
        ("latest", None),
    ),
)
def test_lowest(pin, expected):
    assert cci.lowest(pin) == expected


def test_releases_falls_back_to_stale_cache(repo, monkeypatch):
    path = seed("gitlab", ["19.2"])
    os.utime(path, (time.time() - 100, time.time() - 100))

    def down(url, timeout):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    assert newest("gitlab", 10) == "19.2"


def test_releases_offline(repo):
    path = seed("gitlab", ["19.2"])
    os.utime(path, (0, 0))  # ancient, still used offline
    assert newest("gitlab", 10, offline=True) == "19.2"
    assert cci.releases("ruby", 10, offline=True) is None  # nothing cached, no fetch


def test_broken_cache_file_is_refetched(repo, monkeypatch):
    with open(os.path.join(cci.cache_dir(), "gitlab.json"), "w") as f:
        f.write("[]")
    serve(monkeypatch, ["19.3"])
    assert newest("gitlab", 1000) == "19.3"


def test_tool_pins(repo):
    write(
        repo,
        {
            ".tool-versions": "nodejs 18.0.0\njava temurin-17.0.1\n",
            "mise.toml": '[tools]\nnode = ["22", "20"]\nmaven = {version = "3.9"}\n',
        },
    )
    assert cci.tool_pins(str(repo)) == {
        "nodejs": "22",
        "eclipse-temurin": "temurin-17.0.1",
        "apache-maven": "3.9",
    }


@pytest.mark.parametrize(
    ("files", "expected"),
    (
        ({"main.py": "", ".python-version": "3.12.4\n"}, {"python": "3.12.4"}),
        ({"pyproject.toml": '[project]\nrequires-python = ">=3.11"\n'}, {"python": ">=3.11"}),
        ({"a.py": "", ".tool-versions": "python 3.11.9\n"}, {"python": "3.11.9"}),
        (
            {"package.json": '{"engines": {"node": ">=20"}, "packageManager": "pnpm@9.1.0"}', "pnpm-lock.yaml": ""},
            {"nodejs": ">=20", "pnpm": "9.1.0"},
        ),
        ({"package.json": '{"packageManager": "yarn@4.4.1"}', "bun.lockb": ""}, {"nodejs": None, "bun": None}),
        ({"packages/app/package.json": "{}", ".nvmrc": "v22.1.0\n"}, {"nodejs": "v22.1.0"}),  # monorepo
        ({"deno.json": "{}"}, {"deno": None}),
        ({"go.mod": "module x\n\ngo 1.24.2\n"}, {"go": "1.24.2"}),
        ({"composer.json": '{"require": {"php": "^8.3"}}'}, {"php": "^8.3", "composer": None}),
        ({"src/index.php": ""}, {"php": None, "composer": None}),
        (
            {"pom.xml": "<maven.compiler.release>21</maven.compiler.release>"},
            {"eclipse-temurin": "21", "apache-maven": None},
        ),
        (
            {
                "build.gradle.kts": "java { toolchain { languageVersion.set(JavaLanguageVersion.of(17)) } }",
                "gradle/wrapper/gradle-wrapper.properties": (
                    "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.10.2-bin.zip\n"
                ),
            },
            {"eclipse-temurin": "17", "gradle": "8.10.2"},
        ),
        ({"main.tf": 'terraform {\n  required_version = "~> 1.15.0"\n}\n'}, {"terraform": "~> 1.15.0"}),
        (
            {
                "main.tf": 'terraform {\n  required_version = ">= 1.11"\n}\n',
                "mise.toml": '[tools]\nterraform = "1.16"\n',
            },
            {"terraform": "1.16"},  # exact mise pin beats a range
        ),
        ({"main.tf": "", "mise.toml": '[tools]\nterraform = "latest"\n'}, {"terraform": None}),
        ({"main.tf": "", ".opentofu-version": "1.8.0\n"}, {"opentofu": "1.8.0"}),
        ({"Gemfile": "", ".ruby-version": "3.3.5\n"}, {"ruby": "3.3.5"}),
        ({"Cargo.toml": "", "rust-toolchain.toml": '[toolchain]\nchannel = "1.82.0"\n'}, {"rust": "1.82.0"}),
        ({"node_modules/x/a.py": "", ".gitignore": "node_modules/\n"}, {}),  # ignored files
    ),
)
def test_detect(repo, files, expected):
    write(repo, files)
    assert cci.detect(str(repo), cci.repo_files(str(repo))) == expected


@pytest.mark.parametrize(
    ("files", "expected"),
    (
        ({"main.tf": b"\xff\xfe"}, {"terraform": None}),  # non-UTF-8 bytes
        ({"package.json": '{"engines": "node 20"}'}, {"nodejs": None}),  # wrong-typed container
        ({"package.json": '{"engines": {"node": 20}}'}, {"nodejs": None}),  # non-string leaf
        ({"composer.json": '{"require": "php"}'}, {"php": None, "composer": None}),
        ({"pyproject.toml": 'project = "x"\n'}, {"python": None}),
        ({"Cargo.toml": "", "rust-toolchain.toml": 'toolchain = "stable"\n'}, {"rust": None}),
        ({"main.tf": "", "mise.toml": 'tools = "x"\n'}, {"terraform": None}),
    ),
)
def test_detect_malformed_inputs(repo, files, expected):
    for name, content in files.items():
        if isinstance(content, bytes):
            (repo / name).write_bytes(content)
        else:
            write(repo, {name: content})
    assert cci.detect(str(repo), cci.repo_files(str(repo))) == expected


def annotated(value: str) -> str:
    return HEADER + COMPONENT.replace(
        "  namespace: default\n",
        f"  namespace: default\n  annotations:\n    endoflife.date/products: {value}\n",
    )


def test_location_gets_no_annotation(repo):
    text = HEADER + "---\nkind: Location\nmetadata:\n  name: loc\n  namespace: default\n"
    write(repo, {"catalog-info.yaml": text, "main.py": ""})
    assert run().exit_code == 0
    assert catalog(repo) == text


@pytest.mark.parametrize(
    ("files", "expected"),
    (
        ({"main.py": "", ".python-version": "3.12.4\n"}, "python@3.12"),
        ({"pyproject.toml": '[project]\nrequires-python = ">=3.11"\n'}, "python@3.11"),
        ({"a.py": ""}, "python@3.14"),  # unpinned: newest non-EOL
        (
            {"package.json": '{"engines": {"node": ">=20"}, "packageManager": "pnpm@9.1.0"}', "pnpm-lock.yaml": ""},
            "nodejs@20,pnpm@9",
        ),
        ({"go.mod": "module x\n\ngo 1.24.2\n"}, "go@1.24"),
        ({"composer.json": '{"require": {"php": "^8.3"}}'}, "composer@2.8,php@8.3"),
        ({"main.tf": "", "mise.toml": '[tools]\nterraform = "1.16"\n'}, "terraform@1.16"),
        ({"main.tf": 'terraform {\n  required_version = "~> 1.15.0"\n}\n'}, "terraform@1.15"),
        ({"main.tf": "", "mise.toml": '[tools]\nterraform = "latest"\n'}, "terraform@1.16"),
    ),
)
def test_detects_products(repo, files, expected):
    write(repo, {"catalog-info.yaml": HEADER + COMPONENT, **files})
    assert run().exit_code == 1
    out = catalog(repo)
    assert f"  annotations:\n    endoflife.date/products: {expected}\n" in out
    assert out.index("namespace:") < out.index("annotations:") < out.index("spec:")
    assert run().exit_code == 0  # idempotent


def test_unpinned_skips_eol_cycles(repo):
    seed("python", ["3.14", "3.13"], eol=("3.14",))
    write(repo, {"catalog-info.yaml": HEADER + COMPONENT, "a.py": ""})
    run()
    assert "endoflife.date/products: python@3.13" in catalog(repo)


def test_rewrites_stale_cycle_keeps_extra_products(repo):
    write(
        repo,
        {
            "catalog-info.yaml": annotated("terraform@1.15,gitlab@19.3"),
            "main.tf": "",
            "mise.toml": '[tools]\nterraform = "1.16"\n',
        },
    )
    result = run()
    assert result.exit_code == 1
    assert "updated terraform@1.15 to terraform@1.16" in result.output
    assert "endoflife.date/products: gitlab@19.3,terraform@1.16\n" in catalog(repo)


def test_unpinned_keeps_existing_cycle(repo):
    write(repo, {"catalog-info.yaml": annotated("python@3.11"), "a.py": ""})
    assert run().exit_code == 0


def test_sorts_annotation(repo):
    write(repo, {"catalog-info.yaml": annotated("terraform@1.16, gitlab@19.3")})
    result = run()
    assert result.exit_code == 1
    assert "endoflife.date/products: gitlab@19.3,terraform@1.16\n" in catalog(repo)


@pytest.mark.parametrize(
    ("value", "message"),
    (
        ("gitlab@1.0", "gitlab@1.0: unknown cycle"),
        ("gitlab", "gitlab: missing @cycle"),
        ("../etc@1", "unknown endoflife.date product"),
    ),
)
def test_invalid_annotation(repo, value, message):
    write(repo, {"catalog-info.yaml": annotated(value), "a.py": ""})
    result = run()
    assert result.exit_code == 1
    assert message in result.output
    assert "added python" not in result.output
    assert catalog(repo) == annotated(value)  # an invalid annotation is reported, never rewritten


def test_unknown_product(repo, monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", Message(), None)

    monkeypatch.setattr(urllib.request, "urlopen", not_found)
    write(repo, {"catalog-info.yaml": annotated("nope@1")})
    result = run()
    assert result.exit_code == 1
    assert "nope: unknown endoflife.date product" in result.output


def test_api_unreachable(repo, monkeypatch):
    def down(url, timeout):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    write(repo, {"catalog-info.yaml": annotated("ruby@3.3")})
    result = run()
    assert result.exit_code == 1
    assert "use --offline" in result.output


def test_offline(repo):
    for f in os.listdir(cci.cache_dir()):
        os.remove(os.path.join(cci.cache_dir(), f))
    write(repo, {"catalog-info.yaml": HEADER + COMPONENT, "go.mod": "go 1.24.2\n", "a.py": ""})
    result = run("--offline")
    assert result.exit_code == 1
    assert "python: no version pinned and nothing cached, skipped (--offline)" in result.output
    assert "endoflife.date/products: go@1.24\n" in catalog(repo)


def test_cache_ttl_option(repo, monkeypatch):
    path = seed("gitlab", ["19.2"])  # stale copy without 19.3
    os.utime(path, (time.time() - 100, time.time() - 100))
    serve(monkeypatch, ["19.3"])
    write(repo, {"catalog-info.yaml": annotated("gitlab@19.3")})
    assert run("--cache-ttl", "1000").exit_code == 1  # cache still fresh: 19.3 unknown
    assert run("--cache-ttl", "10").exit_code == 0  # stale: refetched


def test_empty_annotations_key(repo):
    text = HEADER + COMPONENT.replace("  namespace: default\n", "  namespace: default\n  annotations:\n")
    write(repo, {"catalog-info.yaml": text, "go.mod": "go 1.24\n"})
    assert run().exit_code == 1
    assert "  annotations:\n    endoflife.date/products: go@1.24\nspec:" in catalog(repo)
    assert run().exit_code == 0


def test_annotates_every_component(repo):
    second = COMPONENT.replace("name: svc", "name: other").replace("kind: Component", "kind: Resource")
    write(repo, {"catalog-info.yaml": HEADER + COMPONENT + second, "go.mod": "go 1.24\n"})
    assert run().exit_code == 1
    assert catalog(repo).count("endoflife.date/products: go@1.24\n") == 2


TERRAFORM_GITLAB = """\
# yaml-language-server: $schema=https://json.schemastore.org/catalog-info.json
# nonk8s
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: terraform-gitlab
  namespace: default
  title: Terraform GitLab
  description: >
    GitLab configuration as code managed with Terraform.
    Provisions and manages GitLab groups.
  annotations:
    backstage.io/techdocs-ref: dir:.
    gitlab.com/project-slug: devops/terraform-gitlab
    endoflife.date/products: terraform@1.15
  tags:
    - terraform
  links:
    - url: https://gitlab.tnet.ge/devops/terraform-gitlab
      title: GitLab Repository
      icon: code
spec:
  type: infrastructure
  owner: devops
"""


def test_round_trip_keeps_formatting(repo):
    write(
        repo,
        {"catalog-info.yaml": TERRAFORM_GITLAB, "main.tf": "", "mise.toml": '[tools]\nterraform = "1.16"\n'},
    )
    assert run().exit_code == 1
    assert catalog(repo) == TERRAFORM_GITLAB.replace("terraform@1.15", "terraform@1.16")


def test_offline_uses_cache(repo):
    write(
        repo,
        {"catalog-info.yaml": HEADER + COMPONENT, "package.json": '{"engines": {"node": "20.11.0"}}', "a.py": ""},
    )
    assert run("--offline").exit_code == 1
    assert "endoflife.date/products: nodejs@20,python@3.14\n" in catalog(repo)


@pytest.mark.parametrize("body", (b"[]", b'{"result": []}', b"not json"))
def test_bad_payload(repo, monkeypatch, body):
    serve_body(monkeypatch, body)
    write(repo, {"catalog-info.yaml": annotated("ruby@3.3")})
    result = run()
    assert result.exit_code == 1
    assert "ruby: bad endoflife.date API response" in result.output


def test_offline_empty_cache_keeps_correct_annotation(repo):
    for f in os.listdir(cci.cache_dir()):
        os.remove(os.path.join(cci.cache_dir(), f))
    text = annotated("nodejs@20")
    write(repo, {"catalog-info.yaml": text, "package.json": "{}", ".nvmrc": "v20.11.0\n"})
    assert run("--offline").exit_code == 0
    assert catalog(repo) == text


def test_cache_dir_symlink_is_ignored(repo, monkeypatch, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "gitlab.json").write_text(json.dumps({"result": {"releases": [{"name": "1.0", "isEol": False}]}}))
    before = (other / "gitlab.json").read_text()
    os.rename(cci.cache_dir(), tmp_path / "moved")
    os.symlink(other, cci.cache_dir())
    serve(monkeypatch, ["19.3"])
    assert newest("gitlab", 1000) == "19.3"  # seeded file not read
    assert (other / "gitlab.json").read_text() == before  # nothing written through the link
    assert os.listdir(other) == ["gitlab.json"]
    assert cci.releases("gitlab", 1000, offline=True) is None


def test_cache_write_failure_keeps_result(repo, monkeypatch):
    os.remove(os.path.join(cci.cache_dir(), "gitlab.json"))
    serve(monkeypatch, ["19.3"])

    def boom(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(os, "replace", boom)
    assert newest("gitlab", 1000) == "19.3"
    assert "gitlab.json" not in os.listdir(cci.cache_dir())
    assert not [f for f in os.listdir(cci.cache_dir()) if f.startswith("tmp")]  # temp file cleaned up


def test_cache_dir_is_a_file(repo, monkeypatch, tmp_path):
    os.remove(os.path.join(cci.cache_dir(), "gitlab.json"))
    for f in os.listdir(cci.cache_dir()):
        os.remove(os.path.join(cci.cache_dir(), f))
    os.rmdir(cci.cache_dir())
    open(cci.cache_dir(), "w").close()
    serve(monkeypatch, ["19.3"])
    assert newest("gitlab", 1000) == "19.3"


@pytest.mark.parametrize("value", ("oops", "[a]"))
def test_annotations_not_a_mapping(repo, value):
    text = HEADER + COMPONENT.replace("  namespace: default\n", f"  namespace: default\n  annotations: {value}\n")
    write(repo, {"catalog-info.yaml": text, "go.mod": "go 1.24\n"})
    result = run()
    assert result.exit_code == 1
    assert "svc: metadata.annotations must be a mapping" in result.output
    assert "Traceback" not in result.output
    assert catalog(repo) == text


def test_non_utf8_catalog(repo):
    (repo / "catalog-info.yaml").write_bytes(b"\xff\xfe\x00")
    result = run()
    assert result.exit_code == 1
    assert "catalog-info.yaml: not valid UTF-8" in result.output


def test_non_ascii_filename(repo):
    write(repo, {"скрипт.py": ""})
    assert cci.detect(str(repo), cci.repo_files(str(repo))) == {"python": None}


def test_terraform_ignores_commented_required_version(repo):
    write(repo, {"main.tf": '# required_version = "1.0"\nterraform {\n  required_version = "~> 1.15.0"\n}\n'})
    assert cci.detect(str(repo), cci.repo_files(str(repo))) == {"terraform": "~> 1.15.0"}
