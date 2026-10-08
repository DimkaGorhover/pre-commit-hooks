# mise-managed hooks

An alternative to pulling hooks from their upstream hook repositories: install
the tool with [mise](https://mise.jdx.dev) and call the binary from a
`repo: local` hook with `language: system`.

## Why

- **No clone, no build.** An upstream hook repo is cloned and, depending on
    its `language`, built (`golang`), put in a virtualenv (`python`) or pulled
    as an image (`docker`). A system hook just runs the binary.
- **One version source.** The tool version lives in `mise.toml`, so the hook,
    the shell, the IDE and CI all run the same binary. There is no second
    `rev:` to bump.
- **Faster tools.** You can pick a native binary over a Python one, e.g.
    [ryl](ryl.md) (Rust) instead of yamllint (Python).

The trade-off: the tool has to be on `PATH`, which mise handles.

## The pattern

```yaml
repos:
  - repo: local
    hooks:
      - id: <tool>
        name: <description>
        language: system
        entry: <binary>
        args: [] # flags the upstream hook would pass
        types: [] # or files: <regex>
```

```toml
#:schema https://mise.en.dev/schema/mise.json
[settings]
minimum_release_age = "7d" # don't pick up a release younger than a week

[tools]
gitleaks = "latest" # the tool the hook calls
```

Or from the CLI, which writes the same `[tools]` entry:

```sh
mise use gitleaks
```

A `mise` task runs every hook against the whole repo:

```toml
[tasks.pre-commit]
description = "run pre-commit hooks on all files"
run = "prek run --all-files --cd {{config_root}}"
```

!!! tip "Tools not on `PATH`"

    `language: system` needs the binary on `PATH`. That holds in a shell with
    `mise activate`. If commits come from a GUI client without it, prefix the
    entry with `mise exec --`, e.g. `entry: mise exec -- ryl`. mise then
    resolves the version from `mise.toml` itself.

## Hooks

| Hook                                        | Tool                                                  | Replaces                                                 |
| ------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------- |
| [gitleaks](gitleaks.md)                     | [gitleaks](https://github.com/gitleaks/gitleaks)      | `gitleaks/gitleaks`                                      |
| [ryl](ryl.md)                               | [ryl](https://github.com/owenlamont/ryl)              | `adrienverge/yamllint`                                   |
| [shellcheck](shellcheck.md)                 | [shellcheck](https://github.com/koalaman/shellcheck)  | `shellcheck-py/shellcheck-py`                            |
| [shfmt](shfmt.md)                           | [shfmt](https://github.com/mvdan/sh)                  | `scop/pre-commit-shfmt`                                  |
| [ruff](ruff.md)                             | [ruff](https://github.com/astral-sh/ruff)             | `astral-sh/ruff-pre-commit`                              |
| [terraform fmt](terraform-fmt.md)           | [terraform](https://github.com/hashicorp/terraform)   | `antonbabenko/pre-commit-terraform` `terraform_fmt`      |
| [terraform validate](terraform-validate.md) | [terraform](https://github.com/hashicorp/terraform)   | `antonbabenko/pre-commit-terraform` `terraform_validate` |
| [tflint](tflint.md)                         | [tflint](https://github.com/terraform-linters/tflint) | `antonbabenko/pre-commit-terraform` `terraform_tflint`   |
