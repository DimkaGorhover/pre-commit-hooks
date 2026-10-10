# ty

Type checks Python. A faster alternative to mypy and pyright, from the ruff
authors. Still beta (`0.0.x`): rules and defaults change between releases.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: ty
        name: Type Check (ty)
        language: system
        entry: ty
        args:
          - check
        pass_filenames: false # whole project: errors span files
        types:
          - python
```

ty resolves third-party imports from the project's `.venv`, so run `uv sync`
first. Without it every import is reported as unresolved.

## mise

=== "mise.toml"

````
```toml
[tools]
ty = "latest"
```
````

=== "CLI"

````
```sh
mise use ty
```
````

Configure ty in `ty.toml` or `[tool.ty]` in `pyproject.toml`. It reads
`requires-python` for the target version.
