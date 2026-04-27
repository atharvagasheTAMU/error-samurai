from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from core.fingerprints import fingerprint_error, guess_language
from seed.js_records import JS_RECORDS
from seed.python_records import PYTHON_RECORDS
from seed.web_records import WEB_RECORDS
from storage.db import connect_and_init
from storage.incidents import create_incident
from storage.memories import create_memory

SEED_REPO_PATH = "__error_samurai_seed__"


@dataclass(frozen=True)
class SeedResult:
    issues: int
    variants: int
    inserted: int
    skipped: int


def seed_all(connection: sqlite3.Connection | None = None) -> SeedResult:
    owns_connection = connection is None
    connection = connection or connect_and_init()
    existing_keys = _existing_seed_keys(connection)
    inserted = 0
    skipped = 0
    issues = _records()

    for record in issues:
        for index, error_text in enumerate(record["errors"], start=1):
            seed_key = f"{record['key']}:{index}"
            if seed_key in existing_keys:
                skipped += 1
                continue

            language = guess_language(error_text) or _language_from_tags(record["tags"])
            incident = create_incident(
                connection,
                repo_path=SEED_REPO_PATH,
                branch="seed",
                raw_error=error_text,
                fingerprint=fingerprint_error(error_text, language),
                language=language,
                status="closed",
                metadata={"seed_key": seed_key},
            )
            create_memory(
                connection,
                incident_id=incident["id"],
                title=record["title"],
                summary=record["summary"],
                root_cause=record["root_cause"],
                fix_steps=record["fix_steps"],
                confidence=record["confidence"],
                is_trivial=False,
                validated=True,
                metadata={
                    "seed_key": seed_key,
                    "seed_issue_key": record["key"],
                    "source": "error-samurai-seed",
                    "variant_error": error_text,
                },
                tags=sorted(set(record["tags"] + ["seed"])),
            )
            existing_keys.add(seed_key)
            inserted += 1

    if owns_connection:
        connection.close()

    return SeedResult(
        issues=len(issues),
        variants=sum(len(record["errors"]) for record in issues),
        inserted=inserted,
        skipped=skipped,
    )


def _records() -> list[dict[str, Any]]:
    return [*PYTHON_RECORDS, *JS_RECORDS, *WEB_RECORDS]


def _existing_seed_keys(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT metadata_json FROM memories WHERE metadata_json LIKE ?",
        ('%"seed_key"%',
        ),
    ).fetchall()
    keys: set[str] = set()
    for row in rows:
        if not row["metadata_json"]:
            continue
        try:
            metadata = json.loads(row["metadata_json"])
        except json.JSONDecodeError:
            continue
        seed_key = metadata.get("seed_key")
        if isinstance(seed_key, str):
            keys.add(seed_key)
    return keys


def _language_from_tags(tags: list[str]) -> str | None:
    if "python" in tags:
        return "python"
    if "typescript" in tags or "javascript" in tags:
        return "typescript"
    if "web" in tags:
        return "web"
    return None


def main() -> None:
    result = seed_all()
    print(
        "Seeded Error Samurai memories: "
        f"{result.inserted} inserted, {result.skipped} skipped "
        f"({result.issues} issues, {result.variants} variants)."
    )


if __name__ == "__main__":
    main()
