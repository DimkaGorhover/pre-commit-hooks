# shellcheck

Lints shell scripts with [ShellCheck](https://github.com/koalaman/shellcheck).
mise installs the binary directly, so the hook needs neither Docker nor Python.

## Replaces

The official hook,
[shellcheck-precommit](https://github.com/koalaman/shellcheck-precommit), runs
shellcheck in a Docker image:

```yaml
repos:
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.11.0
    hooks:
      - id: shellcheck
```

[shellcheck-py](https://github.com/shellcheck-py/shellcheck-py) is the other
common option and installs the binary through a Python wheel. Both run the
same shellcheck with the same `.shellcheckrc`. Swap either one for the local
hook below.

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
