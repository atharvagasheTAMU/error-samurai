from __future__ import annotations

import hashlib
import sqlite3

from storage.incidents import get_incident


def hash_repo_path(repo_path: str) -> str:
    return hashlib.sha256(repo_path.encode("utf-8")).hexdigest()


def set_active_incident(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
    incident_id: int,
) -> None:
    repo_hash = hash_repo_path(repo_path)
    connection.execute(
        """
        INSERT INTO repo_context (repo_path_hash, repo_path, active_incident_id)
        VALUES (?, ?, ?)
        ON CONFLICT(repo_path_hash) DO UPDATE SET
            repo_path = excluded.repo_path,
            active_incident_id = excluded.active_incident_id,
            updated_at = CURRENT_TIMESTAMP
        """,
        (repo_hash, repo_path, incident_id),
    )
    connection.commit()


def get_active_incident_id(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT active_incident_id
        FROM repo_context
        WHERE repo_path_hash = ?
        """,
        (hash_repo_path(repo_path),),
    ).fetchone()
    if row is None:
        return None
    return row["active_incident_id"]


def get_active_incident(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
) -> dict | None:
    incident_id = get_active_incident_id(connection, repo_path=repo_path)
    if incident_id is None:
        return None
    return get_incident(connection, incident_id)


def clear_active_incident(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
) -> None:
    connection.execute(
        """
        UPDATE repo_context
        SET active_incident_id = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE repo_path_hash = ?
        """,
        (hash_repo_path(repo_path),),
    )
    connection.commit()
