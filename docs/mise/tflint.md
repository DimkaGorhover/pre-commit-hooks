# tflint

Lints Terraform with [tflint](https://github.com/terraform-linters/tflint).
Replaces `terraform_tflint` from
[pre-commit-terraform](https://github.com/antonbabenko/pre-commit-terraform).

## Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: tflint
        name: tflint
        language: system
        entry: tflint
        args:
          - --recursive # every module under the repo root
        pass_filenames: false
        files: \.(tf|tfvars)$
```

tflint lints modules, not single files, so it ignores the file list and walks
the repo with `--recursive`; `files` only decides whether the hook runs.

## mise

=== "mise.toml"

    ```toml
    [tools]
    tflint = "latest"
    ```

=== "CLI"

    ```sh
    mise use tflint
    ```

Rulesets are plugins declared in `.tflint.hcl`:

```hcl
plugin "terraform" {
  enabled = true
  preset  = "all"
}
```

Install the declared plugins once per machine (and in CI) before the hook runs:

```sh
tflint --init
```
