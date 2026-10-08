# Pre-commit Hooks

My personal collection of git hooks for [prek](https://github.com/j178/prek),
also compatible with classic [pre-commit](https://pre-commit.com). It covers
checks I couldn't find in
[pre-commit/pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks)
or wanted to work differently.

Full documentation: <https://dimkagorhover.github.io/pre-commit-hooks/>

## Hooks

| Hook                                                                       | What it does                                                           |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [`check-symlinks-outside-repo`](docs/hooks/check-symlinks-outside-repo.md) | Forbids symlinks whose target resolves outside the repository          |
| [`check-agent-files-tokens`](docs/hooks/check-agent-files-tokens.md)       | Keeps `AGENTS.md`, `CLAUDE.md` and friends under a token budget        |
| [`check-yaml-schema`](docs/hooks/check-yaml-schema.md)                     | Validates YAML against the schema in its `yaml-language-server` header |
| [`mdformat`](docs/hooks/mdformat.md)                                       | Formats Markdown with a shared mdformat plugin set                     |

## Usage

Add the repo to `.pre-commit-config.yaml` and pick the hooks you want:

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>  # no release tags yet, pin a full commit SHA
    hooks:
      - id: check-symlinks-outside-repo
      - id: check-agent-files-tokens
      - id: check-yaml-schema
      - id: mdformat
```

Then install the git hook:

```sh
prek install  # or: pre-commit install
```

## Development

```sh
uv run pytest        # run tests
mise run pre-commit  # lint the repo with its own hooks config
mise run docs:serve  # preview the docs on http://127.0.0.1:8000
```

## License

[MIT](LICENSE)
