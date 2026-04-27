from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RankingContext:
    query: str
    fingerprint: str | None = None
    repo_path: str | None = None
    language: str | None = None


def rank_memories(
    memories: list[dict[str, Any]],
    context: RankingContext,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked = []
    for memory in memories:
        scored = dict(memory)
        scored["score"] = round(_score_memory(scored, context), 3)
        ranked.append(scored)

    ranked.sort(key=lambda item: (item["score"], item.get("created_at") or ""), reverse=True)
    return _dedupe_ranked(ranked)[:limit]


def _score_memory(memory: dict[str, Any], context: RankingContext) -> float:
    score = 0.35
    rank = memory.get("rank")
    if isinstance(rank, (int, float)):
        score += max(0.0, 0.2 - min(abs(rank), 20.0) / 100.0)

    memory_fingerprint = memory.get("incident_fingerprint")
    if context.fingerprint and memory_fingerprint == context.fingerprint:
        score += 0.35
    elif context.fingerprint and _fingerprint_family(memory_fingerprint) == _fingerprint_family(context.fingerprint):
        score += 0.18

    if context.repo_path and memory.get("incident_repo_path") == context.repo_path:
        score += 0.12
    if context.language and memory.get("incident_language") == context.language:
        score += 0.08
    if memory.get("validated"):
        score += 0.08

    score += min(float(memory.get("confidence") or 0.0), 1.0) * 0.2
    score += _recency_boost(memory.get("created_at"))

    if float(memory.get("confidence") or 0.0) < 0.5:
        score -= 0.15

    return max(0.0, min(score, 1.0))


def _fingerprint_family(fingerprint: str | None) -> str | None:
    if not fingerprint:
        return None
    parts = fingerprint.split(".")
    return ".".join(parts[:3]) if len(parts) >= 3 else fingerprint


def _recency_boost(created_at: str | None) -> float:
    if not created_at:
        return 0.0
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created).days
    if age_days <= 30:
        return 0.08
    if age_days <= 180:
        return 0.04
    return -0.05


def _dedupe_ranked(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped = []
    for memory in memories:
        key = _dedupe_key(memory)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(memory)
    return deduped


def _dedupe_key(memory: dict[str, Any]) -> str:
    metadata_json = memory.get("metadata_json")
    if isinstance(metadata_json, str):
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            metadata = {}
        seed_issue_key = metadata.get("seed_issue_key")
        if isinstance(seed_issue_key, str):
            return f"seed:{seed_issue_key}"
    return f"memory:{memory.get('id')}"
