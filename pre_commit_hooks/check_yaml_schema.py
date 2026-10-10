from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from typing import Any

import click
import jsonschema
import yaml
from referencing import Registry, Resource

HEADER = re.compile(r"^#\s*yaml-language-server:\s*\$schema=(\S+)\s*$")


class Loader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2 scalars: dates stay strings, only true/false are bools."""


DROPPED = ("tag:yaml.org,2002:timestamp", "tag:yaml.org,2002:bool")
Loader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag not in DROPPED]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


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


def load_json(uri: str) -> Any:
    if uri.startswith("https://"):
        with urllib.request.urlopen(uri, timeout=30) as r:
            return json.load(r)
    with open(uri, encoding="utf-8") as f:
        return json.load(f)


def retrieve(uri: str) -> Resource:
    """Fetches remote $refs; https only, like the header."""
    if not uri.startswith("https://"):
        raise ValueError(f"only https:// $refs are supported: {uri}")
    return Resource.from_contents(load_json(uri))


# ponytail: no on-disk schema cache, each run re-downloads https schemas; add one if runs get slow
REGISTRY = Registry(retrieve=retrieve)


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

    for uri, files in by_schema.items():
        try:
            schema = load_json(uri)
            cls = jsonschema.validators.validator_for(schema)
            cls.check_schema(schema)
        except (OSError, ValueError, jsonschema.SchemaError) as e:
            click.echo(f"{uri}: cannot load schema: {e}")
            retv = 1
            continue
        validator = cls(schema, registry=REGISTRY, format_checker=cls.FORMAT_CHECKER)
        for filename in files:
            try:
                with open(filename, encoding="utf-8") as f:
                    instance = yaml.load(f, Loader)
            except yaml.YAMLError as e:
                click.echo(f"{filename}: {e}")
                retv = 1
                continue
            for error in validator.iter_errors(instance):
                click.echo(f"{filename}::{error.json_path}: {error.message}")
                retv = 1
    sys.exit(retv)


if __name__ == "__main__":
    main()
