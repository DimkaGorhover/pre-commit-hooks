from __future__ import annotations

import csv
import os
import sys
from pathlib import PurePath

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.tree import Tree

from pre_commit_hooks.util import is_ai_agent, project_dir

TITLE = "Symlinks pointing outside repo"


def _default_format() -> str:
    if is_ai_agent():
        return "csv"
    # prek/CI pipe hook output: keep it greppable, one full path per line
    return "tree" if sys.stdout.isatty() else "plain"


def _can_encode(chars: str) -> bool:
    try:
        chars.encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _echo(rows: list[tuple[str, str]], fmt: str) -> None:
    if fmt in ("table", "tree") and not _can_encode("📁🔗━┃│├└"):
        fmt = "plain"  # e.g. ASCII or cp1252 stdout
    if fmt == "plain":
        for filename, target in rows:
            click.echo(f"{filename}: points outside repo -> {target}")
    elif fmt == "csv":
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(("file", "target"))
        writer.writerows(rows)
    else:
        console = Console(emoji=False, highlight=False)
        console.print(_tree(rows) if fmt == "tree" else _table(rows))


def _table(rows: list[tuple[str, str]]) -> Table:
    table = Table(title=TITLE)
    table.add_column("File", overflow="fold")
    table.add_column("Target", overflow="fold")
    for filename, target in rows:
        table.add_row(escape(filename), escape(target))
    return table


def _tree(rows: list[tuple[str, str]]) -> Tree:
    root = Tree(TITLE)
    dirs: dict[tuple[str, ...], Tree] = {(): root}
    for filename, target in sorted(rows):
        *parents, name = PurePath(filename).parts
        for i in range(1, len(parents) + 1):
            key = tuple(parents[:i])
            if key not in dirs:
                dirs[key] = dirs[key[:-1]].add(f"📁 [bold]{escape(key[-1])}[/bold]")
        dirs[tuple(parents)].add(f"🔗 {escape(name)} -> [red]{escape(target)}[/red]")
    return root


@click.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(("plain", "csv", "table", "tree")),
    default=_default_format,
    help="Output format. Default: csv inside an AI agent, tree on a terminal, plain otherwise.",
)
@click.argument("filenames", nargs=-1)
def main(fmt: str, filenames: tuple[str, ...]) -> int:
    """Checks for symlinks pointing outside the repo root."""
    root = os.path.realpath(project_dir())
    rows = []
    for filename in filenames:
        if not os.path.islink(filename):
            continue
        # non-strict realpath: also resolves broken links and link chains
        target = os.path.realpath(filename)
        if os.path.commonpath([root, target]) != root:
            rows.append((filename, os.readlink(filename)))
    if rows:
        _echo(rows, fmt)
    sys.exit(1 if rows else 0)


if __name__ == "__main__":
    main()
