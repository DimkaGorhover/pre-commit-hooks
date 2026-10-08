# shellcheck

Lints shell scripts. The usual upstream hook,
[shellcheck-py](https://github.com/shellcheck-py/shellcheck-py), installs the
binary through a Python wheel; mise installs the same binary directly.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: shellcheck
        name: shellcheck
        language: system
        entry: shellcheck
        types:
          - shell
```

## mise

=== "mise.toml"

    ```toml
    [tools]
    shellcheck = "latest"
    ```

=== "CLI"

    ```sh
    mise use shellcheck
    ```

Configure checks in a `.shellcheckrc` at the repo root.
