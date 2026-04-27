import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = ".error-samurai"
HOME_ENV_VAR = "ERROR_SAMURAI_HOME"


@dataclass(frozen=True)
class SamuraiPaths:
    base_dir: Path
    db_path: Path
    config_path: Path
    diffs_dir: Path
    logs_dir: Path


def get_base_dir(base_dir: Path | str | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir).expanduser()

    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser()

    return Path.home() / APP_DIR_NAME


def get_paths(base_dir: Path | str | None = None) -> SamuraiPaths:
    root = get_base_dir(base_dir)
    return SamuraiPaths(
        base_dir=root,
        db_path=root / "memory.db",
        config_path=root / "config.yaml",
        diffs_dir=root / "diffs",
        logs_dir=root / "logs",
    )


def ensure_data_dirs(paths: SamuraiPaths | None = None) -> SamuraiPaths:
    resolved = paths or get_paths()
    resolved.base_dir.mkdir(parents=True, exist_ok=True)
    resolved.diffs_dir.mkdir(parents=True, exist_ok=True)
    resolved.logs_dir.mkdir(parents=True, exist_ok=True)
    return resolved
