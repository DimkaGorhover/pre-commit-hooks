# check-catalog-info

Makes sure the repository has a valid Backstage `catalog-info.yaml` at its
root and fixes what it can: the schema header, `metadata.namespace` and the
[endoflife.date](https://endoflife.date) `endoflife.date/products` annotation.
Like `end-of-file-fixer`, it fails the commit when it changed the file, so you
review and stage the fix.

## Usage

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>
    hooks:
      - id: check-catalog-info
```

Runs on every commit (`always_run`, no filenames) on the `pre-commit`,
`pre-push` and `manual` stages.

??? info "Hook definition"

    ```yaml
    --8<-- ".pre-commit-hooks.yaml:check-catalog-info"
    ```

## How it works

- Fails when `catalog-info.yaml` is missing, does not parse, or has no
    entities.
- Adds
    `# yaml-language-server: $schema=https://json.schemastore.org/catalog-info.json`
    when the leading comment block has no `yaml-language-server` header. Pair
    it with [check-yaml-schema](check-yaml-schema.md) to validate against the
    schema.
- Every entity needs `metadata.name`; a missing `metadata.namespace` becomes
    `namespace: default`.
- For `Component` and `Resource` entities the `endoflife.date/products`
    annotation (`product@cycle,...`, sorted) is kept in sync with the repo:
    - products are detected from files in the repo that git does not ignore
        (tracked and untracked) (`*.py` → `python`,
        `package.json` → `nodejs`, lockfiles → `pnpm`/`yarn`/`bun`, `go.mod` →
        `go`, `composer.json`/`*.php` → `php` + `composer`, `pom.xml` →
        `eclipse-temurin` + `apache-maven`, `build.gradle(.kts)` →
        `eclipse-temurin` + `gradle`, `*.tf` → `terraform` or `opentofu`,
        `Gemfile` → `ruby`, `Cargo.toml` → `rust`, `deno.json` → `deno`);
    - the cycle comes from a repo pin: `mise.toml` / `.tool-versions` first,
        then `.python-version`, `requires-python`, `.nvmrc`, `engines.node`,
        `packageManager`, `go.mod`, `require.php`, `required_version`, ...;
    - a pinned cycle that differs from the annotation is rewritten;
    - an unpinned product gets the newest non-EOL cycle, but only when it is
        missing from the annotation;
    - products the hook cannot detect (e.g. `gitlab@19.3`) are kept;
    - every `product@cycle` is checked against
        `https://endoflife.date/api/v1/products/<product>/`.
- API responses are cached in `$TMPDIR/pre-commit-hooks-endoflife/`. A stale
    entry is still used when the API is unreachable. The cache is only used
    when its directory is owned by you and is not a symlink; otherwise the hook
    runs without a cache.
- A file that is already valid is never rewritten; when it is, comments,
    quoting and folded scalars are preserved.

## Example

```console
$ prek run check-catalog-info
check Backstage catalog-info.yaml........................................Failed
- hook id: check-catalog-info
- exit code: 1
- files were modified by this hook

catalog-info.yaml: added yaml-language-server header
catalog-info.yaml: terraform-gitlab: added metadata.namespace: default
catalog-info.yaml: terraform-gitlab: updated terraform@1.15 to terraform@1.16 (repo pin)
```

## Options

| Option        | Default | Description                                                                                             |
| ------------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `--offline`   | off     | No API calls: repo pins plus any cached API response; unpinned products with nothing cached are skipped |
| `--cache-ttl` | `86400` | Seconds an endoflife.date API response stays cached                                                     |

## Run manually

=== "prek"

    ```sh
    prek run check-catalog-info --all-files
    ```

=== "pre-commit"

    ```sh
    pre-commit run check-catalog-info --all-files
    ```

=== "Directly"

    ```sh
    check-catalog-info [--offline] [--cache-ttl SECONDS]
    ```
