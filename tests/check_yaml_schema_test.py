from __future__ import annotations

import pytest
from click.testing import CliRunner

from pre_commit_hooks.check_yaml_schema import main

SCHEMA = '{"type": "object", "required": ["name"]}'


def run(*args: str) -> int:
    return CliRunner().invoke(main, args).exit_code


def invoke(*args: str):
    return CliRunner().invoke(main, args)


@pytest.mark.parametrize(
    ("content", "expected"),
    (
        ("# yaml-language-server: $schema=../schema.json\nname: x\n", 0),
        ("# yaml-language-server: $schema=../schema.json\nother: x\n", 1),
        ("# a comment\n# yaml-language-server: $schema=../schema.json\nother: x\n", 1),
        ("other: x\n", 0),  # no header: skipped
        ("other: x\n# yaml-language-server: $schema=../schema.json\n", 0),  # header after content: ignored
        ("# yaml-language-server: $schema=http://example.com/s.json\nname: x\n", 1),
    ),
)
def test_main(tmpdir, content, expected):
    tmpdir.join("schema.json").write(SCHEMA)
    f = tmpdir.join("d", "f.yaml")
    f.write(content, ensure=True)
    assert run(str(f)) == expected


def test_main_missing_local_schema(tmpdir):
    f = tmpdir.join("f.yaml")
    f.write("# yaml-language-server: $schema=missing.json\nname: x\n")
    assert run(str(f)) != 0


def test_main_yaml_1_2_scalars(tmpdir):
    tmpdir.join("schema.json").write(
        '{"required": ["on"], "properties": {"d": {"type": "string"}, "y": {"type": "string"}}}'
    )
    f = tmpdir.join("f.yaml")
    f.write("# yaml-language-server: $schema=schema.json\non: x\nd: 2024-01-01\ny: yes\n")
    assert run(str(f)) == 0


def test_main_invalid_yaml(tmpdir):
    tmpdir.join("schema.json").write(SCHEMA)
    f = tmpdir.join("f.yaml")
    f.write("# yaml-language-server: $schema=schema.json\nname: [x\n")
    assert run(str(f)) == 1


@pytest.mark.parametrize(
    ("docs", "expected"),
    (("name: a\n---\nname: b\n", 0), ("name: a\n---\nother: b\n", 1)),
)
def test_main_multi_document(tmpdir, docs, expected):
    tmpdir.join("schema.json").write(SCHEMA)
    f = tmpdir.join("f.yaml")
    f.write("# yaml-language-server: $schema=schema.json\n---\n" + docs)
    result = invoke(str(f))
    assert result.exit_code == expected
    if expected:
        assert f"{f}[doc 2]::$: 'name' is a required property" in result.output


def test_main_unresolvable_ref(tmpdir):
    tmpdir.join("schema.json").write('{"$ref": "missing.json"}')  # non-https: retrieve refuses
    f = tmpdir.join("f.yaml")
    f.write("# yaml-language-server: $schema=schema.json\nname: x\n")
    result = invoke(str(f))
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "cannot resolve $ref" in result.output
