# Pre-commit Hooks

Hooks for [prek](https://github.com/j178/prek) (also compatible with classic
[pre-commit](https://pre-commit.com)).

| Hook                                                                | What it does                                                           |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [check-symlinks-outside-repo](hooks/check-symlinks-outside-repo.md) | Forbids symlinks whose target resolves outside the repository          |
| [check-agent-files-tokens](hooks/check-agent-files-tokens.md)       | Keeps `AGENTS.md`, `CLAUDE.md` and friends under a token budget        |
| [`check-yaml-schema`](hooks/check-yaml-schema.md)                   | Validates YAML against the schema in its `yaml-language-server` header |
| [`mdformat`](hooks/mdformat.md)                                     | Formats Markdown with a shared mdformat plugin set                     |

## Quick start

Add the repo to `.pre-commit-config.yaml` and pick the hooks you want:

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>
    hooks:
      - id: check-symlinks-outside-repo
      - id: check-agent-files-tokens
      - id: check-yaml-schema
      - id: mdformat
```

!!! warning "Pin `rev`"

    There are no release tags yet. Pin `rev` to a full commit SHA rather than a
    branch name, so the hooks don't change under you.

Then install the git hook:

=== "prek"

    ```sh
    prek install
    ```

=== "pre-commit"

    ```sh
    pre-commit install
    ```

## Building these docs

```sh
mise run docs:serve  # live preview on http://127.0.0.1:8000
mise run docs:build  # static site in site/
```
