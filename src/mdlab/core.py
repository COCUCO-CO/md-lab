from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_profiles() -> dict[str, Any]:
    with (ROOT / "configs" / "profiles.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "nogit"


def git_status() -> str:
    try:
        return subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unavailable"


def run_id(phase: int, profile: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"phase{phase:02d}_{profile}_{stamp}_{git_sha()}"


def phase_root(phase: int) -> Path:
    return ROOT / "outputs" / f"phase{phase:02d}"


def latest_run(phase: int, profile: str) -> Path:
    root = phase_root(phase)
    matches = sorted(root.glob(f"phase{phase:02d}_{profile}_*"))
    if not matches:
        raise FileNotFoundError(f"No run found for phase {phase}, profile {profile}")
    return matches[-1]


def create_run(phase: int, profile: str, resolved_config: dict[str, Any]) -> Path:
    path = phase_root(phase) / run_id(phase, profile)
    for child in ["prepared", "simulation", "analysis", "figures", "visualization", "logs"]:
        (path / child).mkdir(parents=True, exist_ok=True)
    with (path / "resolved_config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(resolved_config, handle, sort_keys=False)
    manifest = base_manifest(phase, profile)
    manifest["resolved_config_sha256"] = sha256_file(path / "resolved_config.yaml")
    write_json(path / "manifest.json", manifest)
    return path


def base_manifest(phase: int, profile: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": phase,
        "profile": profile,
        "start_utc": utc_now(),
        "end_utc": None,
        "status": "RUNNING",
        "cwd": str(ROOT),
        "command": " ".join(sys.argv),
        "python": sys.version,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git_sha": git_sha(),
        "git_status": git_status(),
        "inputs": {},
        "outputs": {},
        "restarts": [],
    }


def finish_manifest(run_dir: Path, status: str, extra: dict[str, Any] | None = None) -> None:
    path = run_dir / "manifest.json"
    manifest = read_json(path)
    manifest["end_utc"] = utc_now()
    manifest["status"] = status
    if extra:
        manifest.update(extra)
    write_json(path, manifest)


def resolve_config(phase: int, profile: str) -> dict[str, Any]:
    data = load_profiles()
    phase_cfg = data[f"phase{phase}"]
    if profile not in phase_cfg.get("profiles", {}) and phase not in {5, 6, 7}:
        raise ValueError(f"Unknown profile {profile!r} for phase {phase}")
    resolved = dict(data["project_defaults"])
    resolved.update({k: v for k, v in phase_cfg.items() if k != "profiles"})
    if "profiles" in phase_cfg:
        resolved.update(phase_cfg["profiles"][profile])
    resolved["phase"] = phase
    resolved["profile"] = profile
    resolved["seed"] = int(data["project_defaults"]["seed_base"]) + phase * 100 + (0 if profile == "quick" else 1)
    return resolved


def download(url: str, destination: Path, timeout: int = 60) -> dict[str, Any]:
    import requests

    destination.parent.mkdir(parents=True, exist_ok=True)
    provenance_path = destination.with_name(f"{destination.name}.provenance.json")
    if destination.exists():
        if not provenance_path.exists():
            raise RuntimeError(f"Existing immutable input lacks provenance: {destination}")
        provenance = read_json(provenance_path)
        actual_hash = sha256_file(destination)
        if provenance["url"] != url or provenance["sha256"] != actual_hash:
            raise RuntimeError(f"Immutable input provenance mismatch: {destination}")
        return provenance

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    destination.write_bytes(response.content)
    provenance = {
        "url": url,
        "downloaded_utc": utc_now(),
        "path": str(destination.relative_to(ROOT)),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }
    write_json(provenance_path, provenance)
    return provenance


def hardware_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {
        "cpu_count_logical": os.cpu_count(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
    }
    try:
        query = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
        result["nvidia_smi"] = query.splitlines()
    except Exception as exc:
        result["nvidia_smi_error"] = repr(exc)
    return result


def package_versions(names: Iterable[str]) -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    result: dict[str, str] = {}
    for name in names:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "NOT_INSTALLED"
    return result


def openmm_platform(preferred: str = "CUDA", precision: str = "mixed"):
    import openmm

    names = [openmm.Platform.getPlatform(i).getName() for i in range(openmm.Platform.getNumPlatforms())]
    if preferred not in names:
        raise RuntimeError(f"Requested OpenMM platform {preferred!r} unavailable. Available: {names}")
    platform_obj = openmm.Platform.getPlatformByName(preferred)
    properties: dict[str, str] = {}
    if preferred == "CUDA":
        properties = {"Precision": precision}
    return platform_obj, properties, names


def append_csv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


@dataclass
class Timer:
    start: float = 0.0

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_seconds = time.perf_counter() - self.start
