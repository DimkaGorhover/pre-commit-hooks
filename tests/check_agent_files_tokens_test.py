from __future__ import annotations

import pytest
from click.testing import CliRunner

from pre_commit_hooks.check_agent_files_tokens import main


def run(*args: str) -> int:
    return CliRunner().invoke(main, args).exit_code


@pytest.mark.parametrize(
    ("content", "expected"),
    (
        ("", 0),
        ("hello world\n", 0),
        ("word " * 3000, 1),
        ("<|endoftext|>\n", 0),  # special tokens counted as plain text
    ),
)
def test_main(tmpdir, content, expected):
    f = tmpdir.join("AGENTS.md")
    f.write(content)
    assert run(str(f)) == expected


def test_main_max_tokens(tmpdir):
    f = tmpdir.join("CLAUDE.md")
    f.write("word " * 10)
    assert run("--max-tokens", "5", str(f)) == 1
    assert run("--max-tokens", "50", str(f)) == 0


def test_main_reports_all_files(tmpdir):
    big, small = tmpdir.join("AGENTS.md"), tmpdir.join("GEMINI.md")
    big.write("word " * 10)
    small.write("word")
    result = CliRunner().invoke(main, ("--max-tokens", "5", str(big), str(small)))
    assert result.exit_code == 1
    assert "AGENTS.md" in result.output
    assert "GEMINI.md" not in result.output
