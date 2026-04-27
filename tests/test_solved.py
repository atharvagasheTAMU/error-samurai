import json
from pathlib import Path

from core.capture import capture_incident
from core.solved import solve_active_incident
from storage.context import get_active_incident_id
from storage.db import connect_and_init
from storage.incidents import get_incident
from storage.memories import get_memory


def test_solved_creates_memory_and_closes_active_incident(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    incident = capture_incident(
        "pytest fixture 'client' not found",
        cwd=tmp_path,
        connection=connection,
    )

    result = solve_active_incident(
        note="Added a client fixture to conftest.py.",
        cwd=tmp_path,
        connection=connection,
    )

    memory = get_memory(connection, result.memory["id"])
    metadata = json.loads(memory["metadata_json"])

    assert memory["incident_id"] == incident.incident["id"]
    assert "client fixture" in memory["summary"]
    assert metadata["changed_files"] == []
    assert get_incident(connection, incident.incident["id"])["status"] == "closed"
    assert get_active_incident_id(connection, repo_path=str(tmp_path.resolve())) is None


def test_solved_can_close_without_saving_memory(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    incident = capture_incident("CORS blocked by API", cwd=tmp_path, connection=connection)

    result = solve_active_incident(save_memory=False, cwd=tmp_path, connection=connection)

    assert result.skipped is True
    assert result.memory is None
    assert get_incident(connection, incident.incident["id"])["status"] == "closed"
