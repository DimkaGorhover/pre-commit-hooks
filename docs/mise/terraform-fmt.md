# terraform fmt

Formats Terraform files. Replaces `terraform_fmt` from
[pre-commit-terraform](https://github.com/antonbabenko/pre-commit-terraform),
which is a bash wrapper around the same command.

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: terraform-fmt
        name: terraform fmt
        language: system
        entry: terraform fmt
        files: \.(tf|tfvars|tftest\.hcl)$
```

`terraform fmt` takes several files at once and rewrites them in place.

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

For OpenTofu use `tofu fmt` and `mise use opentofu`.
