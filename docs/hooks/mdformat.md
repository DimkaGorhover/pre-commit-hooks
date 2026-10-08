# mdformat

Formats Markdown with [mdformat](https://github.com/hukkin/mdformat) and a
shared plugin set. It replaces the `repo: local` mdformat hook I kept copying
between projects, where the plugin list had started to drift.

## Usage

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>
    hooks:
      - id: mdformat
```

Runs on the `pre-commit` and `manual` stages, on Markdown files. Configure the
formatting itself with a `.mdformat.toml` in the repo.

??? info "Hook definition"

    ```yaml
    --8<-- ".pre-commit-hooks.yaml:mdformat"
    ```

## Plugins

| Plugin                 | Formats                           |
| ---------------------- | --------------------------------- |
| `mdformat-gfm`         | GitHub Flavored Markdown (tables) |
| `mdformat-frontmatter` | YAML front matter                 |
| `mdformat-toc`         | generated tables of contents      |
| `mdformat-config`      | JSON/TOML/YAML code blocks        |
| `mdformat-ruff`        | Python code blocks                |
| `mdformat-shfmt`       | shell code blocks                 |

!!! warning "`shfmt`"

    `mdformat-shfmt` calls the `shfmt` binary (or docker), so install it, for
    example with `mise use shfmt`.

## Changing the plugin set

Setting `additional_dependencies` in your config **replaces** the list above,
so repeat every plugin you want to keep:

```yaml
- id: mdformat
  additional_dependencies:
    - mdformat
    - mdformat-gfm
    - mdformat-mkdocs # admonitions, content tabs
```

## Run manually

=== "prek"

    ```sh
    prek run mdformat --all-files
    ```

=== "pre-commit"

    ```sh
    pre-commit run mdformat --all-files
    ```
