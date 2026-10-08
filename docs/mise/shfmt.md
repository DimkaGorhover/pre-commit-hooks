# shfmt

Formats shell scripts. Replaces
[pre-commit-shfmt](https://github.com/scop/pre-commit-shfmt), which builds shfmt
with Go or runs it in Docker.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: shfmt
        name: Format shell scripts
        language: system
        entry: shfmt
        args:
          - -w # rewrite files; use -d to only show a diff
        types:
          - shell
```

## mise

=== "mise.toml"

    ```toml
    [tools]
    shfmt = "latest"
    ```

=== "CLI"

    ```sh
    mise use shfmt
    ```

shfmt reads indentation and other options from `.editorconfig`, so keep
formatting flags there rather than in `args`.

!!! note

    The [`mdformat`](../hooks/mdformat.md) hook also needs `shfmt` on `PATH`
    to format shell code blocks.
