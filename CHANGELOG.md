# Changelog

## [0.1.0] - 2026-11-12

First release.

### ✨ Added

- **check-symlinks-outside-repo:** 🔗 Fails on symlinks that resolve outside the repository — they leak host-specific paths and break on every other checkout. `--format` picks `plain`, `csv`, `table` or `tree` output; by default it's csv inside an AI agent, tree on a terminal and plain when piped
- **check-agent-files-tokens:** 🧮 Fails when agent guideline files (`AGENTS.md`, `CLAUDE.md`, skill markdown, ...) go over a token budget, 2500 `o200k_base` tokens by default — oversized files eat context and lower instruction adherence
- **check-yaml-schema:** 📐 Validates YAML against the schema declared in its `yaml-language-server` header, including every document of a multi-document file
- **check-catalog-info:** 📇 Requires a root Backstage `catalog-info.yaml` and fixes what it can: adds the schema header, defaults `metadata.namespace`, and keeps the `endoflife.date/products` annotation in sync with the languages and version pins found in the repo. `--offline` and `--cache-ttl` control the endoflife.date cache
- **mdformat:** 📝 Formats Markdown with a shared plugin set that keeps MkDocs admonitions and content tabs intact — projects stop copy-pasting the local hook definition

### 📚 Documentation

- 📖 Documentation site with a page per hook, plus pages showing how to run gitleaks, ryl, shellcheck, shfmt, ruff, terraform fmt/validate and tflint as `repo: local` hooks with tools installed by mise
