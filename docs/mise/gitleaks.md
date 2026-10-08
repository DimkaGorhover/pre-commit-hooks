# gitleaks

Scans the staged changes for hardcoded secrets. The upstream hook uses
`language: golang`, so pre-commit builds gitleaks from source on first run;
this runs the released binary instead.

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
