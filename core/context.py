from __future__ import annotations

from typing import Any

from core.search import SearchOutcome


def format_samurai_context(outcome: SearchOutcome) -> str:
    lines = [
        "ERROR SAMURAI CONTEXT",
        f"Source: {outcome.source}",
        f"Query: {outcome.query}",
        "",
    ]

    if not outcome.results:
        lines.extend(
            [
                "No relevant prior memory found.",
                "",
                "Usefulness: no reusable context available; continue normal debugging.",
            ]
        )
        return "\n".join(lines)

    lines.append("Relevant memories:")
    for index, memory in enumerate(outcome.results, start=1):
        lines.extend(_format_memory(index, memory))

    lines.extend(
        [
            "",
            f"Usefulness: {_usefulness_hint(outcome.results[0])}",
        ]
    )
    return "\n".join(lines)


def _format_memory(index: int, memory: dict[str, Any]) -> list[str]:
    tags = ", ".join(memory.get("tags") or []) or "none"
    diff_path = memory.get("diff_path") or "no diff artifact"
    confidence = float(memory.get("confidence") or 0.0)
    score = float(memory.get("score") or 0.0)

    return [
        "",
        f"Memory {index}:",
        f"Title: {memory['title']}",
        f"Confidence: {confidence:.2f}",
        f"Match score: {score:.2f}",
        f"Root cause: {memory['root_cause']}",
        f"Fix steps: {memory['fix_steps']}",
        f"Tags: {tags}",
        f"Diff: {diff_path}",
    ]


def _usefulness_hint(memory: dict[str, Any]) -> str:
    score = float(memory.get("score") or 0.0)
    confidence = float(memory.get("confidence") or 0.0)

    if score >= 0.75 and confidence >= 0.75:
        return "likely relevant; use this before broad debugging."
    if score >= 0.5 or confidence >= 0.75:
        return "possibly relevant; verify against the current error before applying."
    return "weak match; treat as background context only."
