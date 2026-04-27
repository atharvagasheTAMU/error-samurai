from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SolveSignals:
    fixed_seconds: int | None = None
    files_touched: int | None = None
    lines_changed: int | None = None
    user_force_permanent: bool = False


@dataclass(frozen=True)
class TrivialityResult:
    is_trivial: bool
    score: float
    reasons: list[str] = field(default_factory=list)


TRIVIAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsyntaxerror\b", re.I), "syntax error"),
    (re.compile(r"missing semicolon", re.I), "missing semicolon"),
    (re.compile(r"\btypo\b", re.I), "typo"),
    (re.compile(r"forgot (to )?(npm install|install dependencies)", re.I), "forgot dependency install"),
    (re.compile(r"obvious null check|null check", re.I), "obvious null check"),
)


def classify_triviality(
    error_text: str,
    signals: SolveSignals | None = None,
) -> TrivialityResult:
    signals = signals or SolveSignals()
    if signals.user_force_permanent:
        return TrivialityResult(False, 0.0, ["user requested permanent save"])

    score = 0.0
    reasons: list[str] = []

    for pattern, reason in TRIVIAL_PATTERNS:
        if pattern.search(error_text):
            score += 0.45
            reasons.append(reason)

    if signals.fixed_seconds is not None and signals.fixed_seconds < 30:
        score += 0.25
        reasons.append("fixed in under 30 seconds")

    if signals.files_touched == 1:
        score += 0.15
        reasons.append("single file touched")

    if signals.lines_changed == 1:
        score += 0.2
        reasons.append("one-line diff")

    score = min(score, 1.0)
    return TrivialityResult(score >= 0.5, score, reasons)


def is_trivial_issue(error_text: str, signals: SolveSignals | None = None) -> bool:
    return classify_triviality(error_text, signals).is_trivial
