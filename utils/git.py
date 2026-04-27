from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path | str | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    output = result.stdout.strip()
    return output or None


def get_repo_path(cwd: Path | str | None = None) -> Path:
    repo = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if repo:
        return Path(repo)
    return Path(cwd or Path.cwd()).resolve()


def get_branch(cwd: Path | str | None = None) -> str | None:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def get_changed_files(cwd: Path | str | None = None) -> list[str]:
    output = _run_git(["diff", "--name-only"], cwd)
    if not output:
        return []
    return [line for line in output.splitlines() if line.strip()]


def get_diff(cwd: Path | str | None = None) -> str | None:
    return _run_git(["diff"], cwd)


def is_git_repo(cwd: Path | str | None = None) -> bool:
    return _run_git(["rev-parse", "--is-inside-work-tree"], cwd) == "true"
