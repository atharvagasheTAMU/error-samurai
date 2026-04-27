from core.triviality import SolveSignals, classify_triviality, is_trivial_issue


def test_syntax_error_with_fast_one_line_fix_is_trivial() -> None:
    result = classify_triviality(
        "SyntaxError: invalid syntax",
        SolveSignals(fixed_seconds=10, files_touched=1, lines_changed=1),
    )

    assert result.is_trivial is True
    assert result.score >= 0.5
    assert "syntax error" in result.reasons


def test_reusable_multi_step_issue_is_not_trivial() -> None:
    result = classify_triviality(
        "CI cache reused an incompatible dependency lockfile after a branch switch",
        SolveSignals(fixed_seconds=300, files_touched=4, lines_changed=28),
    )

    assert result.is_trivial is False


def test_user_override_prevents_trivial_classification() -> None:
    result = classify_triviality(
        "SyntaxError: missing semicolon",
        SolveSignals(
            fixed_seconds=5,
            files_touched=1,
            lines_changed=1,
            user_force_permanent=True,
        ),
    )

    assert result.is_trivial is False
    assert result.reasons == ["user requested permanent save"]


def test_is_trivial_issue_wrapper() -> None:
    assert is_trivial_issue(
        "forgot npm install",
        SolveSignals(fixed_seconds=15),
    )
