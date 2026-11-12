# check-symlinks-outside-repo

Fails when a committed symlink points outside the repository. Such links work on
the author's machine and break (or silently point somewhere else) everywhere else.

## Usage

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>
    hooks:
      - id: check-symlinks-outside-repo
```

Runs on the `pre-commit`, `pre-push` and `manual` stages, and only on files git
tracks as symlinks (`types: [symlink]`).

??? info "Hook definition"

    ```yaml
    --8<-- ".pre-commit-hooks.yaml:check-symlinks-outside-repo"
    ```

## How it works

- The repository root is `git rev-parse --show-toplevel` (falls back to the
    current directory outside a git repo), with its own symlinks resolved.
- Each symlink is resolved with a non-strict `realpath`, so link chains are
    followed and broken links are still checked.
- If the resolved target is not inside the root, the hook reports the offending
    links and exits with `1`. Clean runs print nothing.

!!! tip

    Relative and absolute links are both fine as long as they resolve inside the
    repo.

## Example

```console
$ ln -s /etc/hosts hosts
$ git add hosts && prek run check-symlinks-outside-repo
check for symlinks pointing outside repo.................................Failed
hosts: points outside repo -> /etc/hosts
```

Run directly in a terminal, the hook prints a tree instead:

```console
$ check-symlinks-outside-repo hosts
Symlinks pointing outside repo
└── 🔗 hosts -> /etc/hosts
```

Inside an AI agent it prints CSV:

```console
file,target
hosts,/etc/hosts
```

## Options

| Option     | Default                                                       | Description                                      |
| ---------- | ------------------------------------------------------------- | ------------------------------------------------ |
| `--format` | `csv` in an AI agent, `tree` on a terminal, `plain` otherwise | Output format: `plain`, `csv`, `table` or `tree` |

prek and CI capture hook output, so there the default is `plain`.

- `plain` prints one `path: points outside repo -> target` line per link.
- `tree` groups links by directory (📁) and shows each as `🔗 name -> target`.
- `table` is a two-column `File | Target` table.
- `csv` has a `file,target` header and one row per link, for machine parsing.

`table` and `tree` fall back to `plain` when stdout can't encode their box
characters and emoji (e.g. an ASCII or cp1252 console).

The hook counts as running in an AI agent when any of these variables is
non-empty: `CLAUDECODE`, `CURSOR_AGENT`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`GEMINI_CLI`, `OPENCODE`, `AMP_CURRENT_THREAD_ID`, `CLINE_ACTIVE`.

```yaml
      - id: check-symlinks-outside-repo
        args: [--format=table]
```

## Run manually

=== "prek"

    ```sh
    prek run check-symlinks-outside-repo --all-files
    ```

=== "pre-commit"

    ```sh
    pre-commit run check-symlinks-outside-repo --all-files
    ```

=== "Directly"

    ```sh
    check-symlinks-outside-repo path/to/link ...
    ```
