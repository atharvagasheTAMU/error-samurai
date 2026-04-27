from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.fingerprints import fingerprint_error, guess_language
from storage import context
from storage.db import connect_and_init
from storage.incidents import close_active_incidents, create_incident
from utils.git import get_branch, get_repo_path, is_git_repo
from utils.paths import get_paths


@dataclass(frozen=True)
class CaptureResult:
    incident: dict
    replaced_incident: bool


def capture_incident(
    error_text: str,
    *,
    cwd: Path | str | None = None,
    connection: sqlite3.Connection | None = None,
) -> CaptureResult:
    text = error_text.strip()
    if not text:
        raise ValueError("Error text is required.")

    owns_connection = connection is None
    connection = connection or connect_and_init()
    repo_path = str(get_repo_path(cwd))
    active = context.get_active_incident(connection, repo_path=repo_path)

    close_active_incidents(connection, repo_path=repo_path)
    language = guess_language(text)
    incident = create_incident(
        connection,
        repo_path=repo_path,
        branch=get_branch(cwd),
        raw_error=text,
        fingerprint=fingerprint_error(text, language),
        language=language,
        status="active",
        metadata={"is_git_repo": is_git_repo(cwd)},
    )
    context.set_active_incident(connection, repo_path=repo_path, incident_id=incident["id"])

    if owns_connection:
        connection.close()

    return CaptureResult(incident=incident, replaced_incident=active is not None)


def load_last_error() -> str | None:
    last_error_path = get_paths().logs_dir / "last_error.txt"
    if not last_error_path.exists():
        return None
    text = last_error_path.read_text(encoding="utf-8").strip()
    return text or None
