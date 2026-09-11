from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ConfigError, sha256_file
from .governance import audit_all, require_license, require_permission


def register_local_file(
    file_path: Path,
    source_id: str,
    purpose: str,
    license_id: str,
    license_evidence: str,
    output_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    if not file_path.is_file():
        raise ConfigError(f"Local artifact does not exist or is not a file: {file_path}")
    if not license_evidence.startswith(("https://", "http://")):
        raise ConfigError("license_evidence must be an explicit HTTP(S) URL")

    audit, bundle = audit_all()
    if not audit.ok:
        raise ConfigError("Project configuration audit failed before registration")
    source = bundle["sources"].get(source_id)
    if source is None:
        raise ConfigError(f"Unknown source id: {source_id}")
    require_permission(source, purpose, license_id)
    require_license(bundle["policy"], license_id, purpose)

    digest = sha256_file(file_path)
    manifest = {
        "schema_version": 1,
        "artifact_id": f"sha256:{digest}",
        "source_id": source_id,
        "source_homepage": source["homepage"],
        "purpose": purpose,
        "license": license_id,
        "license_evidence": license_evidence,
        "local_path": str(file_path.resolve()),
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "sha256": digest,
        "registered_at_utc": datetime.now(UTC).isoformat(),
    }
    destination_dir = output_dir or bundle["root"] / "data" / "manifests"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{digest}.json"
    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        immutable_fields = ("source_id", "purpose", "license", "sha256", "size_bytes")
        if any(existing.get(key) != manifest[key] for key in immutable_fields):
            raise ConfigError(f"Conflicting manifest already exists: {destination}")
        return destination, existing

    with destination.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return destination, manifest

