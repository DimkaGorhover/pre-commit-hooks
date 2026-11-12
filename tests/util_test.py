from __future__ import annotations

import os
import subprocess

import pytest

from pre_commit_hooks.util import AI_AGENT_ENV_VARS, is_ai_agent, project_dir


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


def test_is_ai_agent_false(no_agent_env):
    assert not is_ai_agent()


def test_is_ai_agent_empty_value(no_agent_env):
    no_agent_env.setenv("CLAUDECODE", "")
    assert not is_ai_agent()


@pytest.mark.parametrize("name", AI_AGENT_ENV_VARS)
def test_is_ai_agent_true(no_agent_env, name):
    no_agent_env.setenv(name, "1")
    assert is_ai_agent()
