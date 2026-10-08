from __future__ import annotations

import os
import sys

import click

from pre_commit_hooks.util import project_dir


@click.command()
@click.argument("filenames", nargs=-1)
def main(filenames: tuple[str, ...]) -> int:
    """Checks for symlinks pointing outside the repo root."""
    root = os.path.realpath(project_dir())
    retv = 0
    for filename in filenames:
        if not os.path.islink(filename):
            continue
        # non-strict realpath: also resolves broken links and link chains
        target = os.path.realpath(filename)
        if os.path.commonpath([root, target]) != root:
            click.echo(f"{filename}: points outside repo -> {os.readlink(filename)}")
            retv = 1
    sys.exit(retv)


if __name__ == "__main__":
    main()
