# check-agent-files-tokens

Fails when an AI agent guideline file exceeds a token budget. These files are
loaded into the agent's context on every session, so every token in them is paid
for on every request. Keep them short and move details into files the agent
reads on demand.

## Usage

```yaml
repos:
  - repo: https://github.com/DimkaGorhover/pre-commit-hooks
    rev: <commit-sha>
    hooks:
      - id: check-agent-files-tokens
        # optional
        args: [--max-tokens=4000, --encoding=cl100k_base]
```

Runs on the `pre-commit`, `pre-push` and `manual` stages.

## Checked files

| Pattern                                                                     | Tool           |
| --------------------------------------------------------------------------- | -------------- |
| `AGENTS.md`, `AGENTS.local.md`                                              | Codex, generic |
| `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/*.md`                        | Claude Code    |
| `GEMINI.md`, `GEMINI.local.md`                                              | Gemini CLI     |
| `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` | GitHub Copilot |
| `.cursorrules`, `.cursor/rules/*.mdc`                                       | Cursor         |
| `.windsurfrules`                                                            | Windsurf       |
| `.clinerules`                                                               | Cline          |

Root-level and nested files (e.g. `services/api/AGENTS.md`) both match. To check
other files, override `files:` in your config.

??? info "Hook definition"

    ```yaml
    --8<-- ".pre-commit-hooks.yaml:check-agent-files-tokens"
    ```

## Options

| Option         | Default      | Description                                                           |
| -------------- | ------------ | --------------------------------------------------------------------- |
| `--max-tokens` | `2500`       | Maximum tokens per file (must be ≥ 1)                                 |
| `--encoding`   | `o200k_base` | [tiktoken](https://github.com/openai/tiktoken) encoding used to count |

The default of 2500 follows Anthropic's advice to keep `CLAUDE.md` under ~200
lines, at roughly 12 tokens per markdown line.

!!! note "The count is an approximation"

    tiktoken encodings are OpenAI's, not every vendor's tokenizer, but they are
    close enough for a budget.

## Example

```console
$ prek run check-agent-files-tokens --all-files
check AI agent guideline files token budget..............................Failed
CLAUDE.md: 3120 tokens > 2500 (move details into on-demand files)
```

## Run manually

=== "prek"

    ```sh
    prek run check-agent-files-tokens --all-files
    ```

=== "pre-commit"

    ```sh
    pre-commit run check-agent-files-tokens --all-files
    ```

=== "Directly"

    ```sh
    check-agent-files-tokens --max-tokens 2500 AGENTS.md CLAUDE.md
    ```
