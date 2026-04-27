from pathlib import Path

from core.search import search_memories_for_query
from seed.seed import seed_all
from storage.db import connect_and_init


def test_seed_dataset_inserts_variants_and_is_idempotent(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")

    first = seed_all(connection)
    second = seed_all(connection)

    assert first.issues == 20
    assert first.variants >= 60
    assert first.inserted == first.variants
    assert second.inserted == 0
    assert second.skipped == first.variants


def test_seeded_memories_are_searchable_before_user_memories(tmp_path: Path) -> None:
    connection = connect_and_init(tmp_path / "memory.db")
    seed_all(connection)

    outcome = search_memories_for_query(
        "pytest import error numpy",
        cwd=tmp_path,
        connection=connection,
    )

    assert outcome.results
    assert outcome.results[0]["title"] == "Numpy import missing in pytest"
    assert "seed" in outcome.results[0]["tags"]
