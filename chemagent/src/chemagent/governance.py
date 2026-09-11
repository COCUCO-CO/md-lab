from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import ConfigError, load_project_bundle, load_toml


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, other: AuditResult) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _load_entries(path: Path, table: str) -> list[dict[str, Any]]:
    values = load_toml(path).get(table)
    if not isinstance(values, list):
        raise ConfigError(f"Expected [[{table}]] entries in {path}")
    if not all(isinstance(value, dict) for value in values):
        raise ConfigError(f"Every [[{table}]] entry in {path} must be a table")
    return values


def load_sources(path: Path) -> dict[str, dict[str, Any]]:
    return _index_entries(_load_entries(path, "sources"), "source", path)


def load_books(path: Path) -> dict[str, dict[str, Any]]:
    return _index_entries(_load_entries(path, "books"), "book", path)


def _index_entries(
    entries: list[dict[str, Any]], kind: str, path: Path
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            raise ConfigError(f"A {kind} in {path} has no non-empty id")
        if entry_id in indexed:
            raise ConfigError(f"Duplicate {kind} id {entry_id!r} in {path}")
        indexed[entry_id] = entry
    return indexed


def _valid_location(value: str) -> bool:
    if value.startswith(("./", "../")):
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def audit_registry(entries: dict[str, dict[str, Any]], kind: str) -> AuditResult:
    result = AuditResult()
    required = {
        "source": {
            "id",
            "name",
            "domain",
            "homepage",
            "license",
            "approval",
            "training_allowed",
            "retrieval_allowed",
            "notes",
        },
        "book": {
            "id",
            "title",
            "authors",
            "edition",
            "homepage",
            "license",
            "approval",
            "training_allowed",
            "retrieval_allowed",
            "notes",
        },
    }[kind]
    for entry_id, entry in entries.items():
        missing = sorted(required - entry.keys())
        if missing:
            result.errors.append(f"{kind} {entry_id}: missing fields {', '.join(missing)}")
        for permission in ("training_allowed", "retrieval_allowed"):
            if permission in entry and not isinstance(entry[permission], bool):
                result.errors.append(f"{kind} {entry_id}: {permission} must be boolean")
        homepage = entry.get("homepage")
        if homepage and not _valid_location(homepage):
            result.errors.append(f"{kind} {entry_id}: invalid homepage {homepage!r}")
        approval = entry.get("approval")
        if approval != "approved":
            result.warnings.append(f"{kind} {entry_id}: disabled pending {approval}")
        if entry.get("benchmark_only") and entry.get("training_allowed"):
            result.errors.append(f"{kind} {entry_id}: benchmark_only cannot allow training")
    return result


def audit_all(root: Path | None = None) -> tuple[AuditResult, dict[str, Any]]:
    bundle = load_project_bundle(root)
    sources = load_sources(bundle["sources_path"])
    books = load_books(bundle["books_path"])
    policy = load_toml(bundle["policy_path"])
    model = load_toml(bundle["model_path"])
    training = load_toml(bundle["training_path"])

    result = audit_registry(sources, "source")
    result.extend(audit_registry(books, "book"))

    licenses = policy.get("licenses", {})
    for key in ("training_allowlist", "retrieval_allowlist", "denied"):
        if not isinstance(licenses.get(key), list):
            result.errors.append(f"policy: licenses.{key} must be a list")

    model_table = model.get("model", {})
    if not model_table.get("id"):
        result.errors.append("model: model.id is required")
    if not model_table.get("revision"):
        result.errors.append("model: model.revision is required")

    if not isinstance(training.get("training"), dict):
        result.errors.append("training: [training] table is required")
    if not isinstance(training.get("pilot_gate"), dict):
        result.errors.append("training: [pilot_gate] table is required")

    return result, {
        **bundle,
        "sources": sources,
        "books": books,
        "policy": policy,
        "model": model,
        "training": training,
    }


def require_permission(
    source: dict[str, Any], purpose: str, record_license: str | None = None
) -> None:
    if purpose not in {"training", "retrieval"}:
        raise ConfigError(f"Unknown purpose: {purpose}")
    source_id = source["id"]
    if source.get("approval") != "approved":
        raise ConfigError(f"Source {source_id} is not approved: {source.get('approval')}")
    if source.get("benchmark_only"):
        raise ConfigError(f"Source {source_id} is benchmark-only")
    if not source.get(f"{purpose}_allowed"):
        raise ConfigError(f"Source {source_id} does not allow {purpose}")
    if record_license is not None and source.get("license") != record_license:
        raise ConfigError(
            f"Source {source_id} license is {source.get('license')}, not {record_license}"
        )


def require_license(policy: dict[str, Any], license_id: str, purpose: str) -> None:
    licenses = policy["licenses"]
    if license_id in licenses.get("denied", []):
        raise ConfigError(f"License {license_id} is denied")
    allowlist = licenses.get(f"{purpose}_allowlist", [])
    if license_id not in allowlist:
        raise ConfigError(f"License {license_id} is not approved for {purpose}")

