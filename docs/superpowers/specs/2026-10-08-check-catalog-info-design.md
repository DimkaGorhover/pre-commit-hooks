# check-catalog-info — design

## Goal

A pre-commit hook (run via prek) that makes sure a repo has a valid Backstage
`catalog-info.yaml` at its root, auto-fixing what it can and failing the commit
when it changed something or found something it cannot fix (like
`end-of-file-fixer`).

## Scope

- Only `<git-root>/catalog-info.yaml`. Nested catalog files are out of scope.
- Every YAML document in the file is checked for `metadata.name` /
    `metadata.namespace`.
- Only `kind: Component` and `kind: Resource` documents get the
    `endoflife.date/products` annotation.
- Dockerfiles are not scanned.
- JSON-schema validation is not repeated here; `check-yaml-schema` covers it
    once the header exists.

## Hook surface

- id / entry: `check-catalog-info`, `language: python`, `always_run: true`,
    `pass_filenames: false`, stages `pre-commit`, `pre-push`, `manual`.
- Registered in `pyproject.toml` `[project.scripts]` and
    `.pre-commit-hooks.yaml`; doc page `docs/hooks/check-catalog-info.md`
    (added to mkdocs nav like the other hooks).
- New dependencies: `ruamel.yaml`, and `tomli` on Python 3.10 (no `tomllib`).
- Flags:
    - `--offline`: no API calls; cycles come from pins and cached API responses.
    - `--cache-ttl SECONDS`: API cache freshness, default `86400`.
- Exit code: `0` when the file is valid and unchanged; `1` when it was fixed
    (each fix printed) or an unfixable problem was found.
- Code: single module `pre_commit_hooks/check_catalog_info.py`, tests in
    `tests/check_catalog_info_test.py`.

## Data flow

1. Read `<git-root>/catalog-info.yaml` (root via `util.project_dir()`).
    Missing → error `catalog-info.yaml not found`.
1. Split the file into a **prelude** (leading `#` and blank lines) and the
    **body** (the rest). ruamel drops comments before the first `---`, so the
    prelude is handled as plain text.
    - No `yaml-language-server:` line in the first comment block (up to the
        first non-`#` line, like `check-yaml-schema`) → prepend
        `# yaml-language-server: $schema=https://json.schemastore.org/catalog-info.json`.
    - A `yaml-language-server:` line with another schema is left untouched.
1. Round-trip the body with ruamel:
    `YAML()`, `preserve_quotes = True`, `indent(mapping=2, sequence=4, offset=2)`,
    `width = 4096`, `explicit_start` matching the source. Verified to reproduce
    the body of the four sample TNET catalog files byte-for-byte. The body is
    re-dumped only when an entity changed, so a valid file is never rewritten.
    Empty documents (e.g. a trailing `---`) are skipped and dropped on rewrite;
    a file with no entities at all is an error.
1. For each document:
    - `metadata.name` missing → error.
    - `metadata.namespace` missing → insert `namespace: default` right after
        `name`.
1. For each `Component` / `Resource` document, rebuild
    `metadata.annotations["endoflife.date/products"]`:
    - Parse the existing value: comma-separated `product@cycle`, whitespace
        trimmed.
    - Detect products in the repo (table below) and resolve each one's cycle.
    - Merge:
        - detected product missing from the annotation → add it;
        - detected product whose cycle comes from a **repo pin** and differs →
            rewrite to the pinned cycle (repo pin is the source of truth);
        - detected but unpinned product already in the annotation → keep its
            cycle (the API's newest cycle only fills in missing products);
        - product only in the annotation (e.g. `gitlab@19.3`) → keep as is.
    - Validate every resulting `product@cycle` against the API (offline:
        against the cache when there is one). If any is invalid the annotation
        is reported and left untouched, never rewritten.
    - Write the value **sorted by product name**, joined with `,`. Create
        `annotations:` if absent. Nothing detected and no existing value → no
        annotation written.
1. If the content changed, write `prelude + body` back, print each fix, exit 1.

## Detection

Files come from `git ls-files --cached --others --exclude-standard` (tracked
plus new untracked files; ignored dirs like `node_modules`, `.venv`,
`.terraform` are skipped). Detection matches files anywhere in the repo, but
pin files (`.python-version`, `package.json`, `go.mod`, ...) are read from the
repo root only; the exception is `required_version`, taken from the first
`*.tf` anywhere in the repo that sets it.

| Detected by                                              | Product(s)                                                                       | Cycle from (first hit wins)                                                                |
| -------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `*.py`, `pyproject.toml`                                 | `python`                                                                         | `.python-version`, `requires-python`                                                       |
| `package.json`                                           | `nodejs`                                                                         | `.nvmrc` / `.node-version`, `engines.node`                                                 |
| `pnpm-lock.yaml` / `yarn.lock` / `bun.lock`, `bun.lockb` | `pnpm` / `yarn` / `bun`                                                          | `packageManager` in `package.json`                                                         |
| `deno.json`, `deno.jsonc`                                | `deno`                                                                           | —                                                                                          |
| `go.mod`                                                 | `go`                                                                             | `go` directive                                                                             |
| `composer.json`, `*.php`                                 | `php`, `composer`                                                                | `require.php` (php)                                                                        |
| `pom.xml`                                                | `eclipse-temurin`, `apache-maven`                                                | `maven.compiler.release` (temurin)                                                         |
| `build.gradle`, `build.gradle.kts`                       | `eclipse-temurin`, `gradle`                                                      | toolchain `languageVersion` (temurin), `gradle/wrapper/gradle-wrapper.properties` (gradle) |
| `*.tf`                                                   | `terraform`, or `opentofu` if `.opentofu-version` exists or mise pins `opentofu` | `required_version`                                                                         |
| `Gemfile`                                                | `ruby`                                                                           | `.ruby-version`                                                                            |
| `Cargo.toml`                                             | `rust`                                                                           | `rust-toolchain.toml`                                                                      |

An exact pin in `mise.toml` / `.mise.toml` `[tools]` or `.tool-versions`
**overrides** the product-specific source (tool name = product name, plus
`node` → `nodejs`, `java` → `eclipse-temurin`, `maven` → `apache-maven`):
it is what actually runs, while `required_version = ">= 1.11"` is only a
floor. Without a usable mise pin (`latest`, `lts`, missing) the table's
source is used. Still nothing → newest non-EOL cycle from the API. In `--offline` mode an unpinned
product is reported as skipped and not added.

### Cycle normalization

- A version or constraint (`3.12.4`, `^3.12`, `>=3.10,<4`, `~> 1.16.0`,
    `v20.11.0`) is reduced to its lowest bound (`3.12.4`, `3.12`, `3.10`,
    `1.16.0`, `20.11.0`).
- The cycle is the **longest** cycle name from the product's API list that is
    equal to the version or a dot-prefix of it (`3.12.4` → `3.12` for python,
    `20.11.0` → `20` for nodejs).
- Offline: fall back to `major.minor` (or `major` when that is all there is).
- `latest` / `lts` (mise) count as no pin.

## endoflife.date API and cache

- `GET https://endoflife.date/api/v1/products/<product>/` via `urllib`,
    30s timeout; cycles are `result.releases[].name`, EOL from
    `result.releases[].isEol`.
- Cache: `$TMPDIR/pre-commit-hooks-endoflife/<product>.json`
    (`tempfile.gettempdir()`), fresh while its mtime is younger than
    `--cache-ttl`. Stale or missing → fetch and overwrite; if the fetch fails, a
    stale entry is used anyway. `--offline` uses any cache entry regardless of
    age and never fetches; only without one does it fall back to `major.minor`
    and skip unpinned products.
- HTTP 404 → unknown product (error). Network failure → error suggesting
    `--offline`.
- Product names must match `^[a-z0-9][a-z0-9.+-]*$` before they are used in
    the URL or the cache path; anything else is an unknown product.

## Errors (fail, no fix)

- `catalog-info.yaml` not found
- YAML parse error
- no entities in the file
- `metadata.name` missing (reported per document index)
- unknown product in the annotation
- cycle not in the product's API cycle list
- API unreachable (online mode)
- `product` without `@cycle` in the annotation

## Testing

pytest, each case a `tmp_path` git repo; the cache dir is pointed at a fixture
dir pre-seeded with product JSON so tests never hit the network.

- missing file fails
- header added; existing non-catalog header kept
- `namespace: default` inserted in every document of a multi-doc file
- missing `metadata.name` fails
- Location-only file gets no annotation
- detection + pin resolution: python, nodejs + pnpm, go, php + composer,
    terraform from `mise.toml`
- stale cycle rewritten; annotation-only product kept
- invalid cycle and unknown product fail
- annotation output sorted
- second run is a no-op (idempotence)
- file shaped like `terraform-gitlab/catalog-info.yaml` already valid → unchanged
    byte-for-byte
- stale cache entry is refetched (TTL)
