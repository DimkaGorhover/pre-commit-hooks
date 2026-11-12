from __future__ import annotations

import pytest

from pre_commit_hooks.util import AI_AGENT_ENV_VARS


@pytest.fixture
def no_agent_env(monkeypatch):
    for name in AI_AGENT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch
