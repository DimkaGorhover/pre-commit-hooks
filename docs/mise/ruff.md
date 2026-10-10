# ruff

Formats and lints Python. Replaces
[ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), which installs
ruff into a virtualenv per hook repo.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: Ruff Format
        language: system
        entry: ruff
        args:
          - format
        types:
          - python

      - id: ruff-check
        name: Ruff Check
        language: system
        entry: ruff
        args:
          - check
          - --fix
        types:
          - python
```

## mise

=== "mise.toml"

    ```toml
    [tools]
    ruff = "latest"
    ```

=== "CLI"

    ```sh
    mise use ruff
    ```

## Config

ruff reads `ruff.toml`, `.ruff.toml` or `pyproject.toml`. Set up a `.ruff.toml`
at the repo root: it keeps ruff config out of `pyproject.toml` and works in
repos without one. This repo's config:

```toml title=".ruff.toml"
--8<-- ".ruff.toml"
```

`select` turns on rule sets beyond ruff's default (`E4`, `E7`, `E9`, `F`); see the
[rules list](https://docs.astral.sh/ruff/rules/).
