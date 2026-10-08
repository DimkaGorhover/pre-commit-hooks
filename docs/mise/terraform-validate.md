# terraform validate

Validates every Terraform module that has a changed `.tf` file. Replaces
`terraform_validate` from
[pre-commit-terraform](https://github.com/antonbabenko/pre-commit-terraform).

## Hook

`terraform validate` works on a directory, not on files, and needs an
initialized module. The entry turns the changed files into their unique
directories, runs `init -backend=false` there (no state access, only
providers and modules), then validates:

```yaml
repos:
  - repo: local
    hooks:
      - id: terraform-validate
        name: terraform validate
        language: system
        entry: >-
          bash -c 'rc=0;
          for d in $(printf "%s\n" "$@" | xargs -n1 dirname | sort -u); do
          terraform -chdir="$d" init -backend=false -input=false >/dev/null &&
          terraform -chdir="$d" validate -no-color || rc=1; done; exit $rc' --
        files: \.tf$
        require_serial: true
```

- The trailing `--` becomes `$0`, so the file names land in `$@`.
- `rc` keeps going after a failed module, so one run reports all of them.
- `require_serial: true` stops parallel batches from running `init` on the
    same directory at once.

!!! warning "Lock files"

    `init` writes `.terraform.lock.hcl` in each validated directory. Commit
    them, or the next `init` picks provider versions again.

## mise

=== "mise.toml"

    ```toml
    [tools]
    terraform = "1.16" # match required_version in versions.tf
    ```

=== "CLI"

    ```sh
    mise use terraform@1.16
    ```
