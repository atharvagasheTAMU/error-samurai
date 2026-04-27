from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def create_incident(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
    raw_error: str,
    branch: str | None = None,
    fingerprint: str | None = None,
    language: str | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cursor = connection.execute(
        """
        INSERT INTO incidents (
            repo_path, branch, raw_error, fingerprint, language, status, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repo_path,
            branch,
            raw_error,
            fingerprint,
            language,
            status,
            json.dumps(metadata) if metadata else None,
        ),
    )
    connection.commit()
    created = get_incident(connection, cursor.lastrowid)
    assert created is not None
    return created


def get_incident(connection: sqlite3.Connection, incident_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM incidents WHERE id = ?",
        (incident_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_active_incident(
    connection: sqlite3.Connection,
    *,
    repo_path: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT *
        FROM incidents
        WHERE repo_path = ? AND status = 'active'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (repo_path,),
    ).fetchone()
    return _row_to_dict(row)


def close_incident(connection: sqlite3.Connection, incident_id: int) -> None:
    connection.execute(
        """
        UPDATE incidents
        SET status = 'closed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (incident_id,),
    )
    connection.commit()


def close_active_incidents(connection: sqlite3.Connection, *, repo_path: str) -> None:
    connection.execute(
        """
        UPDATE incidents
        SET status = 'closed', updated_at = CURRENT_TIMESTAMP
        WHERE repo_path = ? AND status = 'active'
        """,
        (repo_path,),
    )
    connection.commit()
