# ryl

Lints YAML with [ryl](https://github.com/owenlamont/ryl), a yamllint-compatible
linter written in Rust. It replaces the Python
[yamllint](https://github.com/adrienverge/yamllint) hook and reads the same
`.yamllint.yaml` config.

## Replaces

The upstream yamllint hook installs yamllint into a Python virtualenv:

```yaml
repos:
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.38.0
    hooks:
      - id: yamllint
        args:
          - --no-warnings # report errors only
```

ryl is a drop-in replacement: same CLI flags, same config, no Python. Swap
the hook for the local one below.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: ryl
        name: Lint YAML
        language: system
        entry: ryl
        args:
          - --no-warnings # report errors only
        types:
          - yaml
```

## mise

ryl is not in the mise registry, so install it from its GitHub releases.

=== "mise.toml"

    ```toml
    [tools]
    ryl = "latest"

    [tool_alias]
    ryl = "github:owenlamont/ryl"
    ```

    The alias keeps the short name in `[tools]`.

=== "CLI"

    ```sh
    mise use github:owenlamont/ryl
    ```

    This writes `"github:owenlamont/ryl" = "latest"` to `[tools]`.

To move to ryl's native config, `ryl --migrate-configs --migrate-write`
converts `.yamllint.yaml` into `.ryl.toml`.
