from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ConfigError, sha256_file
from .governance import audit_all, require_license, require_permission


@dataclass(frozen=True)
class BuildSummary:
    counts: dict[str, int]
    input_sha256: str
    output_dir: Path


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    if not path.is_file():
        raise ConfigError(f"JSONL input does not exist: {path}")
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ConfigError(f"Line {line_number} is not a JSON object")
            yield line_number, value


def _group_split(split_group: str) -> str:
    bucket = int(hashlib.sha256(split_group.encode()).hexdigest()[:8], 16) % 1000
    if bucket < 940:
        return "train"
    if bucket < 970:
        return "validation"
    return "test"


def _validate_messages(messages: Any, label: str) -> None:
    if not isinstance(messages, list) or len(messages) < 2:
        raise ConfigError(f"{label}: messages must contain at least two turns")
    allowed_roles = {"system", "user", "assistant", "tool"}
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ConfigError(f"{label}: message {index} is not an object")
        if message.get("role") not in allowed_roles:
            raise ConfigError(f"{label}: message {index} has an invalid role")
        if not isinstance(message.get("content"), str) or not message["content"].strip():
            raise ConfigError(f"{label}: message {index} has empty content")
    if messages[-1].get("role") != "assistant":
        raise ConfigError(f"{label}: final message must be from assistant")


def _validate_record(
    record: dict[str, Any], line_number: int, bundle: dict[str, Any]
) -> str:
    label = f"line {line_number}"
    required = set(bundle["policy"]["records"]["required_fields"])
    missing = sorted(required - record.keys())
    if missing:
        raise ConfigError(f"{label}: missing fields {', '.join(missing)}")
    if not isinstance(record["record_id"], str) or not record["record_id"]:
        raise ConfigError(f"{label}: record_id must be non-empty")
    if not isinstance(record["split_group"], str) or not record["split_group"]:
        raise ConfigError(f"{label}: split_group must be non-empty")
    _validate_messages(record["messages"], label)

    source_ids = record["source_ids"]
    if not isinstance(source_ids, list) or not source_ids:
        raise ConfigError(f"{label}: source_ids must be a non-empty list")
    license_id = record["license"]
    require_license(bundle["policy"], license_id, "training")
    for source_id in source_ids:
        source = bundle["sources"].get(source_id)
        if source is None:
            raise ConfigError(f"{label}: unknown source {source_id}")
        require_permission(source, "training", license_id)

    if not isinstance(record["license_evidence"], str) or not record[
        "license_evidence"
    ].startswith(("https://", "http://")):
        raise ConfigError(f"{label}: license_evidence must be an HTTP(S) URL")
    if license_id != "CC0-1.0" and not record.get("attribution"):
        raise ConfigError(f"{label}: attribution is required for {license_id}")
    if not isinstance(record["evidence"], list) or not record["evidence"]:
        raise ConfigError(f"{label}: evidence must contain source record identifiers")
    if record["observation_kind"] not in bundle["policy"]["records"][
        "allowed_observation_kinds"
    ]:
        raise ConfigError(f"{label}: invalid observation_kind")
    if not isinstance(record["procedural"], bool):
        raise ConfigError(f"{label}: procedural must be boolean")
    if not isinstance(record["safety_tags"], list):
        raise ConfigError(f"{label}: safety_tags must be a list")
    blocked = set(bundle["policy"]["safety"]["blocked_procedural_tags"])
    if record["procedural"] and blocked.intersection(record["safety_tags"]):
        raise ConfigError(f"{label}: blocked procedural safety tag")

    split = record.get("split") or _group_split(record["split_group"])
    if split not in {"train", "validation", "test"}:
        raise ConfigError(f"{label}: split must be train, validation or test")
    return split


def build_sft(input_path: Path, output_dir: Path) -> BuildSummary:
    audit, bundle = audit_all()
    if not audit.ok:
        raise ConfigError("Project configuration audit failed before dataset build")
    if output_dir.exists():
        raise ConfigError(f"Output directory already exists; refusing overwrite: {output_dir}")

    records_by_split: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    seen_ids: set[str] = set()
    group_splits: dict[str, str] = {}
    for line_number, record in _iter_jsonl(input_path):
        split = _validate_record(record, line_number, bundle)
        record_id = record["record_id"]
        if record_id in seen_ids:
            raise ConfigError(f"line {line_number}: duplicate record_id {record_id}")
        seen_ids.add(record_id)
        group = record["split_group"]
        previous = group_splits.setdefault(group, split)
        if previous != split:
            raise ConfigError(f"split_group {group!r} leaks across {previous} and {split}")
        output_record = dict(record)
        output_record["split"] = split
        output_record["content_sha256"] = hashlib.sha256(
            json.dumps(record["messages"], sort_keys=True).encode()
        ).hexdigest()
        records_by_split[split].append(output_record)

    if not seen_ids:
        raise ConfigError("Input dataset has no records")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        for split, records in records_by_split.items():
            with (staging / f"{split}.jsonl").open("x", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        counts = {split: len(records) for split, records in records_by_split.items()}
        audit_payload = {
            "schema_version": 1,
            "input_path": str(input_path.resolve()),
            "input_sha256": sha256_file(input_path),
            "counts": counts,
            "unique_record_ids": len(seen_ids),
            "unique_split_groups": len(group_splits),
            "source_counts": dict(
                Counter(
                    source
                    for records in records_by_split.values()
                    for record in records
                    for source in record["source_ids"]
                )
            ),
        }
        with (staging / "audit.json").open("x", encoding="utf-8") as handle:
            json.dump(audit_payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(staging, output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return BuildSummary(counts, sha256_file(input_path), output_dir)
