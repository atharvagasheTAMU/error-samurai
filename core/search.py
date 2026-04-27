from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.fingerprints import fingerprint_error, guess_language
from core.ranking import RankingContext, rank_memories
from samurai.config import load_config
from storage.context import get_active_incident
from storage.db import connect_and_init
from storage.memories import search_memory_candidates
from utils.git import get_repo_path


@dataclass(frozen=True)
class SearchOutcome:
    query: str
    source: str
    results: list[dict[str, Any]]
    active_incident: dict[str, Any] | None = None


def search_memories_for_query(
    query: str | None = None,
    *,
    cwd: Path | str | None = None,
    connection: sqlite3.Connection | None = None,
    limit: int | None = None,
) -> SearchOutcome:
    owns_connection = connection is None
    connection = connection or connect_and_init()
    config = load_config(create=False)
    max_results = limit or int(config["max_results"])
    repo_path = str(get_repo_path(cwd))
    active_incident = None

    if query and query.strip():
        search_text = query.strip()
        language = guess_language(search_text)
        fingerprint = fingerprint_error(search_text, language)
        source = "query"
    else:
        active_incident = get_active_incident(connection, repo_path=repo_path)
        if active_incident is None or active_incident.get("status") != "active":
            if owns_connection:
                connection.close()
            raise LookupError("No active incident found for this repo. Run `samurai capture` first.")
        search_text = active_incident["raw_error"]
        language = active_incident.get("language")
        fingerprint = active_incident.get("fingerprint")
        source = "active incident"

    candidates = search_memory_candidates(
        connection,
        search_text,
        fingerprint=fingerprint,
        limit=max(max_results * 5, 10),
    )
    ranked = rank_memories(
        candidates,
        RankingContext(
            query=search_text,
            fingerprint=fingerprint,
            repo_path=repo_path,
            language=language,
        ),
        limit=max_results,
    )

    if owns_connection:
        connection.close()

    return SearchOutcome(
        query=search_text,
        source=source,
        results=ranked,
        active_incident=active_incident,
    )
