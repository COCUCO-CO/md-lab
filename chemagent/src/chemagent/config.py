from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a project configuration is missing or inconsistent."""


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Configuration file does not exist: {path}")
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc


def resolve_project_path(value: str, root: Path | None = None) -> Path:
    base = root or project_root()
    path = Path(value)
    return path if path.is_absolute() else base / path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_project_bundle(root: Path | None = None) -> dict[str, Any]:
    base = root or project_root()
    project_path = base / "configs" / "project.toml"
    project = load_toml(project_path)
    paths = project.get("paths")
    if not isinstance(paths, dict):
        raise ConfigError(f"Missing [paths] table in {project_path}")

    required = ("source_registry", "book_registry", "policy", "model", "training")
    missing = [key for key in required if not isinstance(paths.get(key), str)]
    if missing:
        raise ConfigError(f"Missing project paths: {', '.join(missing)}")

    return {
        "root": base,
        "project_path": project_path,
        "project": project,
        "sources_path": resolve_project_path(paths["source_registry"], base),
        "books_path": resolve_project_path(paths["book_registry"], base),
        "policy_path": resolve_project_path(paths["policy"], base),
        "model_path": resolve_project_path(paths["model"], base),
        "training_path": resolve_project_path(paths["training"], base),
    }

