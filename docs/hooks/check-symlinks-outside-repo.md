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
- If the resolved target is not inside the root, the hook prints the offending
    link and exits with `1`.

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

## Options

None.

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
