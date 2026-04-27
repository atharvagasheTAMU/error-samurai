from pathlib import Path

from samurai.config import DEFAULT_CONFIG, load_config, save_config
from utils.git import get_branch, get_changed_files, get_diff, get_repo_path, is_git_repo
from utils.paths import ensure_data_dirs, get_paths


def test_paths_resolve_expected_files(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    assert paths.base_dir == tmp_path
    assert paths.db_path == tmp_path / "memory.db"
    assert paths.config_path == tmp_path / "config.yaml"
    assert paths.diffs_dir == tmp_path / "diffs"
    assert paths.logs_dir == tmp_path / "logs"


def test_ensure_data_dirs_creates_runtime_directories(tmp_path: Path) -> None:
    paths = ensure_data_dirs(get_paths(tmp_path))

    assert paths.base_dir.is_dir()
    assert paths.diffs_dir.is_dir()
    assert paths.logs_dir.is_dir()


def test_load_config_creates_defaults(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    config = load_config(paths=paths)

    assert config == DEFAULT_CONFIG
    assert paths.config_path.exists()


def test_load_config_merges_user_values(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    save_config({"max_results": 5, "output_mode": "plain"}, paths=paths)

    config = load_config(paths=paths)

    assert config["max_results"] == 5
    assert config["output_mode"] == "plain"
    assert config["confidence_threshold"] == DEFAULT_CONFIG["confidence_threshold"]


def test_git_helpers_degrade_outside_git_repo(tmp_path: Path) -> None:
    assert get_repo_path(tmp_path) == tmp_path.resolve()
    assert get_branch(tmp_path) is None
    assert get_changed_files(tmp_path) == []
    assert get_diff(tmp_path) is None
    assert is_git_repo(tmp_path) is False
