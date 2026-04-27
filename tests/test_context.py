from pathlib import Path

from core.capture import capture_incident
from core.context import format_samurai_context
from core.search import search_memories_for_query
from storage.db import connect_and_init
from storage.memories import create_memory


def test_context_formats_active_incident_memory(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    prior = capture_incident(
        "ModuleNotFoundError: No module named 'numpy'",
        cwd=tmp_path,
        connection=connection,
    )
    create_memory(
        connection,
        incident_id=prior.incident["id"],
        title="Numpy import missing",
        summary="pytest failed because numpy was not installed in the active environment.",
        root_cause="The virtual environment was missing numpy.",
        fix_steps="Install numpy through the project environment and rerun pytest.",
        confidence=0.9,
        tags=["python"],
    )
    capture_incident(
        "ModuleNotFoundError: No module named 'numpy'",
        cwd=tmp_path,
        connection=connection,
    )

    outcome = search_memories_for_query(cwd=tmp_path, connection=connection)
    context = format_samurai_context(outcome)

    assert "ERROR SAMURAI CONTEXT" in context
    assert "Source: active incident" in context
    assert "Title: Numpy import missing" in context
    assert "Confidence: 0.90" in context
    assert "Root cause: The virtual environment was missing numpy." in context
    assert "Fix steps: Install numpy through the project environment and rerun pytest." in context
    assert "Usefulness: likely relevant" in context


def test_context_formats_no_results(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")

    outcome = search_memories_for_query(
        "unmatched deploy proxy timeout",
        cwd=tmp_path,
        connection=connection,
    )
    context = format_samurai_context(outcome)

    assert "ERROR SAMURAI CONTEXT" in context
    assert "Source: query" in context
    assert "No relevant prior memory found." in context
    assert "Usefulness: no reusable context available" in context
