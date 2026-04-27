from __future__ import annotations

import sqlite3
from pathlib import Path

from utils.paths import ensure_data_dirs, get_paths

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    branch TEXT,
    raw_error TEXT NOT NULL,
    fingerprint TEXT,
    language TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_repo_status
ON incidents(repo_path, status);

CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint
ON incidents(fingerprint);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    fix_steps TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.75,
    is_trivial INTEGER NOT NULL DEFAULT 0,
    validated INTEGER NOT NULL DEFAULT 1,
    diff_path TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_memory_id
ON tags(memory_id);

CREATE TABLE IF NOT EXISTS repo_context (
    repo_path_hash TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    active_incident_id INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (active_incident_id) REFERENCES incidents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS temp_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    summary TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory_id UNINDEXED,
    title,
    summary,
    root_cause,
    fix_steps
);

PRAGMA user_version = 1;
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    if db_path is None:
        paths = ensure_data_dirs(get_paths())
        db_path = paths.db_path

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    _ensure_column(connection, "memories", "metadata_json", "TEXT")
    connection.commit()


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def connect_and_init(db_path: Path | str | None = None) -> sqlite3.Connection:
    connection = connect(db_path)
    init_db(connection)
    return connection
