# gitleaks

Scans the staged changes for hardcoded secrets with
[gitleaks](https://github.com/gitleaks/gitleaks). mise installs the released
binary, so nothing is built on first run.

## Replaces

The upstream hook uses `language: golang`, so pre-commit builds gitleaks from
source on first run:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks # or gitleaks-docker (Docker image)
```

It runs the same `gitleaks git --pre-commit --redact --staged --verbose` and
reads the same `.gitleaks.toml`. Upstream also ships `gitleaks-system`, which
expects gitleaks on `PATH` like the local hook below, but pins its arguments
in `entry`. The local hook adds `--no-banner` and a size cap.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      # https://github.com/gitleaks/gitleaks/blob/master/.pre-commit-hooks.yaml
      - id: gitleaks
        name: Detect hardcoded secrets
        language: system
        entry: gitleaks
        args:
          - git
          - --pre-commit
          - --redact
          - --no-banner
          - --staged
          - --verbose
          - --max-target-megabytes=10
        pass_filenames: false
```

`pass_filenames: false`: gitleaks reads the staged diff from git itself.

## mise

=== "mise.toml"

    ```toml
    [tools]
    gitleaks = "latest"
    ```

=== "CLI"

    ```sh
    mise use gitleaks
    ```

Configure rules and allowlists in a `.gitleaks.toml` at the repo root, with
`[extend] useDefault = true` to keep the built-in rules.
