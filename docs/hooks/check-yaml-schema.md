# check-yaml-schema

Validates YAML files against the JSON schema they declare in a
`yaml-language-server` header, the same header VS Code and other editors use
for completion. The editor and the commit check read the schema from the same
header, so you only declare it once.

## Usage

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: v0.1.0
    hooks:
      - id: check-yaml-schema
```

Runs on the `pre-commit`, `pre-push` and `manual` stages, on YAML files.

??? info "Hook definition"

    ```yaml
    --8<-- ".pre-commit-hooks.yaml:check-yaml-schema"
    ```

## How it works

- Only the leading comment block is read. The header must appear before the
    first non-comment line, and files without it are skipped.
- `https://` schemas are used as-is. `http://` schemas fail the hook.
- Local schema paths are resolved relative to the YAML file, like
    yaml-language-server does.
- Files are grouped by schema and checked with
    [check-jsonschema](https://github.com/python-jsonschema/check-jsonschema),
    which runs once per schema.
- Multi-document files (`---`) are checked document by document, and errors
    name the document (`f.yaml[doc 2]::$.name: ...`).
- A `$ref` that can't be fetched or found fails the file with
    `cannot resolve $ref`.

## Example

```yaml
# yaml-language-server: $schema=https://json.schemastore.org/github-workflow.json
name: ci
on: push
```

```console
$ prek run check-yaml-schema
check YAML against its declared JSON schema..............................Failed
Schema validation errors were encountered.
  bad.yaml::$: 'name' is a required property
```

## Options

None.

## Run manually

=== "prek"

    ```sh
    prek run check-yaml-schema --all-files
    ```

=== "pre-commit"

    ```sh
    pre-commit run check-yaml-schema --all-files
    ```

=== "Directly"

    ```sh
    check-yaml-schema path/to/file.yaml ...
    ```
