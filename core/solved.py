from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.triviality import SolveSignals, classify_triviality
from samurai.config import load_config
from storage.context import clear_active_incident, get_active_incident
from storage.db import connect_and_init
from storage.incidents import close_incident
from storage.memories import create_memory
from utils.git import get_changed_files, get_diff, get_repo_path
from utils.paths import ensure_data_dirs, get_paths


@dataclass(frozen=True)
class DiffMetadata:
    changed_files: list[str]
    additions: int
    removals: int
    tests_modified: bool
    config_files_modified: bool


@dataclass(frozen=True)
class SolvedResult:
    incident: dict[str, Any]
    memory: dict[str, Any] | None
    diff_metadata: DiffMetadata
    trivial_reasons: list[str]
    skipped: bool = False


def solve_active_incident(
    *,
    note: str | None = None,
    save_memory: bool = True,
    force_permanent: bool = False,
    cwd: Path | str | None = None,
    connection: sqlite3.Connection | None = None,
) -> SolvedResult:
    owns_connection = connection is None
    connection = connection or connect_and_init()
    repo_path = str(get_repo_path(cwd))
    incident = get_active_incident(connection, repo_path=repo_path)
    if incident is None or incident.get("status") != "active":
        if owns_connection:
            connection.close()
        raise LookupError("No active incident found for this repo. Run `samurai capture` first.")

    diff_text = get_diff(cwd) or ""
    diff_metadata = collect_diff_metadata(cwd=cwd, diff_text=diff_text)
    signals = SolveSignals(
        files_touched=len(diff_metadata.changed_files),
        lines_changed=diff_metadata.additions + diff_metadata.removals,
        user_force_permanent=force_permanent,
    )
    triviality = classify_triviality(incident["raw_error"], signals)

    memory = None
    if save_memory:
        diff_path = _write_diff_artifact(incident["id"], diff_text)
        memory = create_memory(
            connection,
            incident_id=incident["id"],
            title=_title_from_error(incident["raw_error"]),
            summary=_summary_from_incident(incident, note),
            root_cause=note.strip() if note and note.strip() else "Solved locally; root cause was inferred from the captured error and code changes.",
            fix_steps=_fix_steps(diff_metadata, note),
            confidence=_confidence(diff_metadata, triviality.is_trivial),
            is_trivial=triviality.is_trivial,
            validated=True,
            diff_path=str(diff_path) if diff_path else None,
            metadata={
                "changed_files": diff_metadata.changed_files,
                "additions": diff_metadata.additions,
                "removals": diff_metadata.removals,
                "tests_modified": diff_metadata.tests_modified,
                "config_files_modified": diff_metadata.config_files_modified,
                "trivial_reasons": triviality.reasons,
            },
            tags=_tags_for_incident(incident, diff_metadata),
        )

    close_incident(connection, incident["id"])
    clear_active_incident(connection, repo_path=repo_path)

    if owns_connection:
        connection.close()

    return SolvedResult(
        incident=incident,
        memory=memory,
        diff_metadata=diff_metadata,
        trivial_reasons=triviality.reasons,
        skipped=not save_memory,
    )


def collect_diff_metadata(
    *,
    cwd: Path | str | None = None,
    diff_text: str = "",
) -> DiffMetadata:
    changed_files = get_changed_files(cwd)
    additions = 0
    removals = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            removals += 1

    return DiffMetadata(
        changed_files=changed_files,
        additions=additions,
        removals=removals,
        tests_modified=any(_is_test_file(path) for path in changed_files),
        config_files_modified=any(_is_config_file(path) for path in changed_files),
    )


def _write_diff_artifact(incident_id: int, diff_text: str) -> Path | None:
    config = load_config(create=False)
    if not config.get("store_diffs", True) or not diff_text.strip():
        return None

    paths = ensure_data_dirs(get_paths())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    diff_path = paths.diffs_dir / f"incident-{incident_id}-{timestamp}.patch"
    diff_path.write_text(diff_text, encoding="utf-8")
    return diff_path


def _title_from_error(error_text: str) -> str:
    first_line = error_text.strip().splitlines()[0]
    return first_line[:80] or "Solved debugging incident"


def _summary_from_incident(incident: dict[str, Any], note: str | None) -> str:
    if note and note.strip():
        return note.strip()
    return f"Resolved captured error: {_title_from_error(incident['raw_error'])}"


def _fix_steps(diff_metadata: DiffMetadata, note: str | None) -> str:
    steps = []
    if note and note.strip():
        steps.append(note.strip())
    if diff_metadata.changed_files:
        steps.append("Review the changed files from the original fix: " + ", ".join(diff_metadata.changed_files))
    if diff_metadata.tests_modified:
        steps.append("Tests were updated as part of the fix.")
    if not steps:
        steps.append("Apply the same local fix that resolved the captured incident.")
    return "\n".join(f"- {step}" for step in steps)


def _confidence(diff_metadata: DiffMetadata, is_trivial: bool) -> float:
    confidence = 0.7
    if diff_metadata.changed_files:
        confidence += 0.08
    if diff_metadata.tests_modified:
        confidence += 0.07
    if is_trivial:
        confidence -= 0.15
    return round(max(0.4, min(confidence, 0.95)), 2)


def _tags_for_incident(incident: dict[str, Any], diff_metadata: DiffMetadata) -> list[str]:
    tags = []
    if incident.get("language"):
        tags.append(incident["language"])
    if incident.get("fingerprint"):
        tags.append(incident["fingerprint"].split(".")[0])
    if diff_metadata.tests_modified:
        tags.append("tests")
    if diff_metadata.config_files_modified:
        tags.append("config")
    return sorted(set(tags))


def _is_test_file(path: str) -> bool:
    lowered = path.lower()
    return "test" in Path(lowered).parts or lowered.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))


def _is_config_file(path: str) -> bool:
    name = Path(path).name.lower()
    return name in {
        "pyproject.toml",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "webpack.config.js",
        ".env",
    } or name.endswith((".yaml", ".yml", ".toml", ".ini", ".cfg"))
