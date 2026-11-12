from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from pre_commit_hooks.check_symlinks_outside_repo import main


def run(*args: str) -> int:
    return CliRunner().invoke(main, args).exit_code


xfail_symlink = pytest.mark.xfail(os.name == "nt", reason="No symlink support")


@xfail_symlink
@pytest.mark.parametrize(
    ("dest", "expected"),
    (
        ("d/f", 0),
        ("d/missing", 0),  # broken but inside: not this hook's job
        ("d/../d/f", 0),
        ("../outside", 1),
        ("d/../../outside", 1),
        ("/etc/hosts", 1),
    ),
)
def test_main(tmpdir, dest, expected):  # pragma: no cover (symlinks)
    repo = tmpdir.join("repo").ensure_dir()
    repo.join("d", "f").ensure()
    with repo.as_cwd():
        os.symlink(dest, "link")
        assert run("link") == expected


@xfail_symlink
def test_main_absolute_inside(tmpdir):  # pragma: no cover (symlinks)
    tmpdir.join("f").ensure()
    with tmpdir.as_cwd():
        os.symlink(str(tmpdir.join("f")), "link")
        assert run("link") == 0


@xfail_symlink
def test_main_chain_escapes(tmpdir):  # pragma: no cover (symlinks)
    repo = tmpdir.join("repo").ensure_dir()
    with repo.as_cwd():
        os.symlink("..", "up")
        os.symlink("up/outside", "link")
        assert run("link") == 1


def test_main_normal_file(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join("f").ensure()
        assert run("f") == 0


@pytest.fixture(autouse=True)
def pinned_console(monkeypatch):
    # rich reads these; keep output independent of the developer's terminal
    for name in ("FORCE_COLOR", "NO_COLOR", "TTY_COMPATIBLE", "TTY_INTERACTIVE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("COLUMNS", "80")


def invoke(*args: str, charset: str = "utf-8"):
    return CliRunner(charset=charset).invoke(main, args)


@xfail_symlink
@pytest.mark.parametrize(
    ("agent", "args", "expected"),
    (
        ("1", (), "file,target\nlink,../outside\n"),
        ("", (), "link: points outside repo -> ../outside\n"),  # piped, not a tty
        ("", ("--format", "plain"), "link: points outside repo -> ../outside\n"),
        ("", ("--format", "csv"), "file,target\nlink,../outside\n"),
        ("1", ("--format", "table"), "┃ File ┃ Target"),
        ("1", ("--format", "tree"), "🔗 link -> ../outside"),
    ),
)
def test_main_format(tmpdir, no_agent_env, agent, args, expected):  # pragma: no cover (symlinks)
    no_agent_env.setenv("CLAUDECODE", agent)
    repo = tmpdir.join("repo").ensure_dir()
    with repo.as_cwd():
        os.symlink("../outside", "link")
        result = invoke(*args, "link")
    assert result.exit_code == 1
    assert expected in result.output


def test_default_format_tty(no_agent_env, monkeypatch):
    from pre_commit_hooks import check_symlinks_outside_repo as mod

    monkeypatch.setattr(mod.sys.stdout, "isatty", lambda: True)
    assert mod._default_format() == "tree"


def test_main_clean_is_silent(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join("f").ensure()
        result = invoke("--format", "csv", "f")
    assert (result.exit_code, result.output) == (0, "")


@xfail_symlink
def test_main_table_escapes_and_folds(tmpdir):  # pragma: no cover (symlinks)
    long_target = "/tmp/" + "z" * 100
    repo = tmpdir.join("repo").ensure_dir()
    with repo.as_cwd():
        repo.join("[slug]").ensure_dir()
        os.symlink("/tmp/[/red]x", "[slug]/:smile:")
        os.symlink(long_target, "long")
        result = invoke("--format", "table", "[slug]/:smile:", "long")
    assert result.exit_code == 1, result.output
    assert "[slug]/:smile:" in result.output
    assert "/tmp/[/red]x" in result.output
    assert "…" not in result.output
    assert "".join(c for c in result.output if c == "z") == "z" * 100


@xfail_symlink
@pytest.mark.parametrize("fmt", ("table", "tree"))
def test_main_ascii_stdout_falls_back_to_plain(tmpdir, fmt):  # pragma: no cover (symlinks)
    with tmpdir.as_cwd():
        os.symlink("/etc/hosts", "link")
        result = invoke("--format", fmt, "link", charset="ascii")
    assert (result.exit_code, result.output) == (1, "link: points outside repo -> /etc/hosts\n")


@xfail_symlink
def test_main_format_tree(tmpdir):  # pragma: no cover (symlinks)
    repo = tmpdir.join("repo").ensure_dir()
    with repo.as_cwd():
        repo.join("docs", "sub").ensure_dir()
        os.symlink("/etc/hosts", "top")
        os.symlink("../../outside", "docs/a.md")
        os.symlink("/[red]x", "docs/sub/b")  # markup in target must stay literal
        result = invoke("--format", "tree", "docs/sub/b", "top", "docs/a.md")
    assert result.exit_code == 1
    assert result.output == (
        "Symlinks pointing outside repo\n"
        "├── 📁 docs\n"
        "│   ├── 🔗 a.md -> ../../outside\n"
        "│   └── 📁 sub\n"
        "│       └── 🔗 b -> /[red]x\n"
        "└── 🔗 top -> /etc/hosts\n"
    )
