from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import defaultdict

import click

HEADER = re.compile(r"^#\s*yaml-language-server:\s*\$schema=(\S+)\s*$")


def find_schema(filename: str) -> str | None:
    """Schema from the leading comment block's yaml-language-server header, or None."""
    with open(filename, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                return None  # header must be in the leading comment block
            match = HEADER.match(line)
            if match:
                schema = match.group(1)
                if schema.startswith("http://"):
                    raise ValueError(f"insecure http:// schema URL: {schema}")
                if schema.startswith("https://"):
                    return schema
                # local paths are relative to the YAML file, like yaml-language-server
                return os.path.realpath(os.path.join(os.path.dirname(filename), schema))
    return None


@click.command()
@click.argument("filenames", nargs=-1)
def main(filenames: tuple[str, ...]) -> int:
    """Validates YAML files against the schema in their yaml-language-server header."""
    by_schema: dict[str, list[str]] = defaultdict(list)
    retv = 0
    for filename in filenames:
        try:
            schema = find_schema(filename)
        except ValueError as e:
            click.echo(f"{filename}: {e}")
            retv = 1
            continue
        if schema:
            by_schema[schema].append(filename)

    for schema, files in by_schema.items():
        cmd = (sys.executable, "-m", "check_jsonschema", "--schemafile", schema, *files)
        retv |= subprocess.run(cmd).returncode
    sys.exit(retv)


if __name__ == "__main__":
    main()
