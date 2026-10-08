from __future__ import annotations

import sys

import click
import tiktoken

# Anthropic: "target under 200 lines per CLAUDE.md"; ~12 tokens per markdown line.
DEFAULT_MAX_TOKENS = 2500


@click.command()
@click.argument("filenames", nargs=-1)
@click.option("--max-tokens", type=click.IntRange(min=1), default=DEFAULT_MAX_TOKENS, show_default=True)
@click.option("--encoding", type=click.Choice(tiktoken.list_encoding_names()), default="o200k_base", show_default=True)
def main(filenames: tuple[str, ...], max_tokens: int, encoding: str) -> int:
    """Checks AI agent guideline files (AGENTS.md, CLAUDE.md, ...) stay under a token budget."""
    enc = tiktoken.get_encoding(encoding)
    retv = 0
    for filename in filenames:
        with open(filename, encoding="utf-8") as f:
            tokens = len(enc.encode(f.read(), disallowed_special=()))
        if tokens > max_tokens:
            click.echo(f"{filename}: {tokens} tokens > {max_tokens} (move details into on-demand files)")
            retv = 1
    sys.exit(retv)


if __name__ == "__main__":
    main()
