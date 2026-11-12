from __future__ import annotations

import os
import subprocess


def project_dir() -> str:
    """Git top-level dir of the cwd, or the cwd itself outside a git repo."""
    try:
        out = subprocess.run(
            ("git", "rev-parse", "--show-toplevel"),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):  # git missing / not a repo
        return os.getcwd()
    return out or os.getcwd()


# Vars AI coding agents set in the shells they spawn.
AI_AGENT_ENV_VARS = (
    "CLAUDECODE",  # Claude Code
    "CURSOR_AGENT",  # Cursor
    "CODEX_SANDBOX",  # Codex
    "CODEX_THREAD_ID",  # Codex
    "GEMINI_CLI",  # Gemini CLI
    "OPENCODE",  # opencode
    "AMP_CURRENT_THREAD_ID",  # Amp
    "CLINE_ACTIVE",  # Cline
)


def is_ai_agent() -> bool:
    """True when running inside an AI coding agent (any known var non-empty)."""
    return any(os.environ.get(name) for name in AI_AGENT_ENV_VARS)
