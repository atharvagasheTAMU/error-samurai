from pathlib import Path

from core.capture import capture_incident
from storage.context import get_active_incident
from storage.db import connect_and_init
from storage.incidents import get_incident


def test_capture_creates_active_incident(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")

    result = capture_incident(
        "ModuleNotFoundError: No module named 'numpy'",
        cwd=tmp_path,
        connection=connection,
    )

    active = get_active_incident(connection, repo_path=str(tmp_path.resolve()))
    assert result.incident["fingerprint"] == "python.import.numpy.missing"
    assert result.incident["language"] == "python"
    assert active is not None
    assert active["id"] == result.incident["id"]


def test_second_capture_replaces_previous_active_incident(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")

    first = capture_incident("pytest fixture 'client' not found", cwd=tmp_path, connection=connection)
    second = capture_incident("CORS blocked by API", cwd=tmp_path, connection=connection)

    assert second.replaced_incident is True
    assert get_incident(connection, first.incident["id"])["status"] == "closed"
    assert get_active_incident(connection, repo_path=str(tmp_path.resolve()))["id"] == second.incident["id"]
