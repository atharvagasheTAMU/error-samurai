from pathlib import Path

from storage.context import (
    clear_active_incident,
    get_active_incident,
    get_active_incident_id,
    set_active_incident,
)
from storage.db import connect_and_init
from storage.incidents import close_incident, create_incident, get_incident
from storage.memories import create_memory, get_memory, search_memories


def test_database_initializes_schema(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")

    user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert user_version == 1


def test_incident_crud_and_active_context(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    incident = create_incident(
        connection,
        repo_path="/repo",
        branch="main",
        raw_error="ModuleNotFoundError: No module named 'numpy'",
        fingerprint="python.import.numpy.missing",
        language="python",
    )

    set_active_incident(connection, repo_path="/repo", incident_id=incident["id"])

    assert get_incident(connection, incident["id"])["raw_error"].startswith("Module")
    assert get_active_incident_id(connection, repo_path="/repo") == incident["id"]
    assert get_active_incident(connection, repo_path="/repo")["id"] == incident["id"]

    clear_active_incident(connection, repo_path="/repo")
    close_incident(connection, incident["id"])

    assert get_active_incident_id(connection, repo_path="/repo") is None
    assert get_incident(connection, incident["id"])["status"] == "closed"


def test_memory_crud_with_tags_and_fts(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    incident = create_incident(
        connection,
        repo_path="/repo",
        raw_error="pytest fixture 'client' not found",
        fingerprint="python.pytest.fixture.client.missing",
        language="python",
    )

    memory = create_memory(
        connection,
        incident_id=incident["id"],
        title="Pytest fixture client missing",
        summary="A test requested a fixture that was never registered.",
        root_cause="conftest.py did not expose a client fixture.",
        fix_steps="Add a client fixture in conftest.py and import the app.",
        confidence=0.9,
        tags=["pytest", "python"],
    )

    fetched = get_memory(connection, memory["id"])
    results = search_memories(connection, "pytest fixture", limit=3)

    assert fetched is not None
    assert fetched["tags"] == ["pytest", "python"]
    assert results[0]["id"] == memory["id"]
    assert results[0]["tags"] == ["pytest", "python"]
