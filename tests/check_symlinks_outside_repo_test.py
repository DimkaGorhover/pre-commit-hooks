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
