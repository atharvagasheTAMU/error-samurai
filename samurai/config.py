from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from utils.paths import SamuraiPaths, ensure_data_dirs, get_paths

DEFAULT_CONFIG: dict[str, Any] = {
    "auto_search": False,
    "output_mode": "auto",
    "confidence_threshold": 0.75,
    "store_diffs": True,
    "temp_cache_ttl_hours": 24,
    "max_results": 3,
}


def load_config(
    config_path: Path | str | None = None,
    *,
    create: bool = True,
    paths: SamuraiPaths | None = None,
) -> dict[str, Any]:
    resolved_paths = paths or get_paths()
    path = Path(config_path) if config_path is not None else resolved_paths.config_path

    if not path.exists():
        if create:
            save_config(DEFAULT_CONFIG, path, paths=resolved_paths)
        return DEFAULT_CONFIG.copy()

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    return {**DEFAULT_CONFIG, **loaded}


def save_config(
    config: dict[str, Any],
    config_path: Path | str | None = None,
    *,
    paths: SamuraiPaths | None = None,
) -> Path:
    resolved_paths = paths or get_paths()
    ensure_data_dirs(resolved_paths)
    path = Path(config_path) if config_path is not None else resolved_paths.config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path
