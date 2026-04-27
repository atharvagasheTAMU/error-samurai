from __future__ import annotations

import json
import re
import sqlite3
from typing import Any


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _tags_for_memory(connection: sqlite3.Connection, memory_id: int) -> list[str]:
    rows = connection.execute(
        "SELECT tag FROM tags WHERE memory_id = ? ORDER BY tag",
        (memory_id,),
    ).fetchall()
    return [row["tag"] for row in rows]


def _with_tags(connection: sqlite3.Connection, memory: dict[str, Any] | None) -> dict[str, Any] | None:
    if memory is None:
        return None
    memory["tags"] = _tags_for_memory(connection, memory["id"])
    return memory


def create_memory(
    connection: sqlite3.Connection,
    *,
    incident_id: int | None,
    title: str,
    summary: str,
    root_cause: str,
    fix_steps: str,
    confidence: float = 0.75,
    is_trivial: bool = False,
    validated: bool = True,
    diff_path: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    cursor = connection.execute(
        """
        INSERT INTO memories (
            incident_id, title, summary, root_cause, fix_steps,
            confidence, is_trivial, validated, diff_path, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            incident_id,
            title,
            summary,
            root_cause,
            fix_steps,
            confidence,
            int(is_trivial),
            int(validated),
            diff_path,
            json.dumps(metadata) if metadata else None,
        ),
    )
    memory_id = cursor.lastrowid

    for tag in tags or []:
        connection.execute(
            "INSERT INTO tags (memory_id, tag) VALUES (?, ?)",
            (memory_id, tag),
        )

    connection.execute(
        """
        INSERT INTO memories_fts (
            memory_id, title, summary, root_cause, fix_steps
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (memory_id, title, summary, root_cause, fix_steps),
    )
    connection.commit()

    created = get_memory(connection, memory_id)
    assert created is not None
    return created


def get_memory(connection: sqlite3.Connection, memory_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM memories WHERE id = ?",
        (memory_id,),
    ).fetchone()
    return _with_tags(connection, _row_to_dict(row))


def search_memories(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []

    rows = connection.execute(
        """
        SELECT
            memories.*,
            bm25(memories_fts) AS rank
        FROM memories_fts
        JOIN memories ON memories.id = memories_fts.memory_id
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (fts_query, limit),
    ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        memory = dict(row)
        memory["tags"] = _tags_for_memory(connection, memory["id"])
        results.append(memory)
    return results


def search_memory_candidates(
    connection: sqlite3.Connection,
    query: str,
    *,
    fingerprint: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    candidates: dict[int, dict[str, Any]] = {}
    fts_query = _to_fts_query(query)

    if fts_query:
        rows = connection.execute(
            """
            SELECT
                memories.*,
                incidents.repo_path AS incident_repo_path,
                incidents.fingerprint AS incident_fingerprint,
                incidents.language AS incident_language,
                incidents.raw_error AS incident_raw_error,
                bm25(memories_fts) AS rank
            FROM memories_fts
            JOIN memories ON memories.id = memories_fts.memory_id
            LEFT JOIN incidents ON incidents.id = memories.incident_id
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        for row in rows:
            memory = dict(row)
            memory["tags"] = _tags_for_memory(connection, memory["id"])
            candidates[memory["id"]] = memory

    if fingerprint:
        rows = connection.execute(
            """
            SELECT
                memories.*,
                incidents.repo_path AS incident_repo_path,
                incidents.fingerprint AS incident_fingerprint,
                incidents.language AS incident_language,
                incidents.raw_error AS incident_raw_error,
                0.0 AS rank
            FROM memories
            JOIN incidents ON incidents.id = memories.incident_id
            WHERE incidents.fingerprint = ?
            ORDER BY memories.created_at DESC, memories.id DESC
            LIMIT ?
            """,
            (fingerprint, limit),
        ).fetchall()
        for row in rows:
            memory = dict(row)
            memory["tags"] = _tags_for_memory(connection, memory["id"])
            candidates[memory["id"]] = memory

    return list(candidates.values())[:limit]


def _to_fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    return " OR ".join(f'"{token}"' for token in tokens)
