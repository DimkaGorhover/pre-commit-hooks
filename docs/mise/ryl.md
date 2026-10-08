# ryl

Lints YAML with [ryl](https://github.com/owenlamont/ryl), a yamllint-compatible
linter written in Rust. It replaces the Python
[yamllint](https://github.com/adrienverge/yamllint) hook and reads the same
`.yamllint.yaml` config.

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
