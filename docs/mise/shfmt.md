# shfmt

Formats shell scripts with [shfmt](https://github.com/mvdan/sh). mise installs
the binary directly, so the hook needs neither Python, Go nor Docker.

## Replaces

The usual upstream hook,
[pre-commit-shfmt](https://github.com/scop/pre-commit-shfmt), installs shfmt
through a Python wheel:

```yaml
repos:
  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.14.1-1
    hooks:
      - id: shfmt # or shfmt-src (Go build), shfmt-docker (Docker image)
```

It runs the same shfmt with `--write` and reads the same `.editorconfig`. Swap
it for the local hook below.

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
