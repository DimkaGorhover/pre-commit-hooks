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

Configure ruff in `ruff.toml`, `.ruff.toml` or `pyproject.toml`.
