from __future__ import annotations

import os
import subprocess

from pre_commit_hooks.util import project_dir


def test_project_dir_git_subdir(tmpdir):
    subprocess.run(("git", "init", "-q", str(tmpdir)), check=True)
    with tmpdir.join("a", "b").ensure_dir().as_cwd():
        assert os.path.realpath(project_dir()) == os.path.realpath(tmpdir)


def test_project_dir_not_git(tmpdir, monkeypatch):
    # stop git from finding a repo in tmpdir's parents
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmpdir.dirpath()))
    with tmpdir.as_cwd():
        assert project_dir() == os.getcwd()


def test_project_dir_no_git_binary(tmpdir, monkeypatch):
    monkeypatch.setenv("PATH", "")
    with tmpdir.as_cwd():
        assert project_dir() == os.getcwd()
