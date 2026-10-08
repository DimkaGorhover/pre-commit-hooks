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
