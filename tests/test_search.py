from pathlib import Path

from core.capture import capture_incident
from core.search import search_memories_for_query
from storage.db import connect_and_init
from storage.memories import create_memory


def test_search_uses_active_incident_when_query_is_omitted(tmp_path: Path) -> None:
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

    assert outcome.source == "active incident"
    assert outcome.results[0]["title"] == "Numpy import missing"
    assert outcome.results[0]["score"] > 0.8


def test_free_text_search_returns_ranked_memory(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    incident = capture_incident("pytest fixture 'client' not found", cwd=tmp_path, connection=connection)
    create_memory(
        connection,
        incident_id=incident.incident["id"],
        title="Pytest client fixture missing",
        summary="A test requested the client fixture before conftest registered it.",
        root_cause="conftest.py did not expose the application test client.",
        fix_steps="Add the client fixture in conftest.py.",
        confidence=0.85,
        tags=["pytest", "python"],
    )

    outcome = search_memories_for_query("pytest client fixture", cwd=tmp_path, connection=connection)

    assert outcome.source == "query"
    assert outcome.results[0]["title"] == "Pytest client fixture missing"
