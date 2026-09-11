from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass

from .config import resolve_project_path
from .governance import audit_all


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _gpu_checks(expected_count: int, minimum_memory_mib: int) -> list[Check]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return [Check("nvidia-smi", False, str(exc))]
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "nvidia-smi failed"
        return [Check("nvidia-smi", False, detail)]

    rows = [row.strip() for row in result.stdout.splitlines() if row.strip()]
    checks = [
        Check("gpu-count", len(rows) >= expected_count, f"found {len(rows)}, need {expected_count}")
    ]
    for row in rows[:expected_count]:
        fields = [field.strip() for field in row.split(",")]
        try:
            memory = int(fields[2])
        except (IndexError, ValueError):
            checks.append(Check("gpu-memory", False, f"could not parse row: {row}"))
            continue
        checks.append(
            Check(
                f"gpu-{fields[0]}-memory",
                memory >= minimum_memory_mib,
                f"{fields[1]}: {memory} MiB, need >= {minimum_memory_mib} MiB",
            )
        )
    return checks


def run_preflight(level: str) -> tuple[bool, list[Check]]:
    if level not in {"governance", "training"}:
        raise ValueError(f"Unknown preflight level: {level}")
    audit, bundle = audit_all()
    free_disk_gib = shutil.disk_usage(bundle["root"]).free / 1024**3
    checks = [
        Check(
            "configuration",
            audit.ok,
            f"{len(audit.errors)} errors, {len(audit.warnings)} gated sources/books",
        ),
        Check("python", sys.version_info >= (3, 11), sys.version.split()[0]),
        Check(
            "free-disk",
            shutil.disk_usage(bundle["root"]).free >= 50 * 1024**3,
            f"{free_disk_gib:.1f} GiB free; governance floor 50 GiB",
        ),
    ]
    if level == "training":
        project = bundle["project"]["project"]
        checks.extend(
            _gpu_checks(project["expected_gpu_count"], project["minimum_gpu_memory_mib"])
        )
        for package in (
            "accelerate",
            "bitsandbytes",
            "datasets",
            "peft",
            "safetensors",
            "torch",
            "transformers",
        ):
            available = importlib.util.find_spec(package) is not None
            checks.append(
                Check(
                    f"python-package:{package}",
                    available,
                    "installed" if available else "missing",
                )
            )
        revision = bundle["model"].get("model", {}).get("revision")
        checks.append(
            Check(
                "model-revision",
                bool(revision and revision != "PIN_BEFORE_TRAINING"),
                str(revision),
            )
        )
        data = bundle["training"].get("data", {})
        for key in ("train_file", "validation_file"):
            path = resolve_project_path(data.get(key, ""), bundle["root"])
            checks.append(Check(key, path.is_file(), str(path)))
        train_path = resolve_project_path(data.get("train_file", ""), bundle["root"])
        audit_path = train_path.parent / "audit.json"
        checks.append(Check("dataset-audit", audit_path.is_file(), str(audit_path)))
    return all(check.ok or not check.required for check in checks), checks


def report_json(checks: list[Check]) -> str:
    return json.dumps([asdict(check) for check in checks], indent=2, sort_keys=True)
