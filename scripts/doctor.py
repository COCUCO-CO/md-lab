#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mdlab.core import hardware_snapshot, package_versions, utc_now, write_json


def main() -> None:
    report = {
        "utc": utc_now(),
        "hardware": hardware_snapshot(),
        "packages": package_versions(
            ["openmm", "openmmforcefields", "openff-toolkit", "pdbfixer", "MDAnalysis", "mdtraj", "numpy"]
        ),
        "checks": {},
    }
    try:
        import openmm
        from openmm import Platform

        platforms = []
        for i in range(Platform.getNumPlatforms()):
            p = Platform.getPlatform(i)
            platforms.append({"name": p.getName(), "speed": p.getSpeed()})
        report["openmm_platforms"] = platforms
        report["checks"]["cuda_available"] = any(p["name"] == "CUDA" for p in platforms)
        report["openmm_version"] = openmm.__version__
    except Exception as exc:
        report["checks"]["openmm_import"] = False
        report["openmm_error"] = repr(exc)

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "openmm.testInstallation"], capture_output=True, text=True, timeout=180
        )
        report["openmm_test"] = {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        report["checks"]["openmm_test_pass"] = completed.returncode == 0
    except Exception as exc:
        report["checks"]["openmm_test_pass"] = False
        report["openmm_test_error"] = repr(exc)

    report["checks"]["nvidia_visible"] = "nvidia_smi" in report["hardware"]
    report["checks"]["enough_ram_hint"] = True
    write_json(ROOT / "state" / "doctor.json", report)
    print(json.dumps(report, indent=2))
    if not all(report["checks"].values()):
        raise SystemExit("Doctor checks failed. Read state/doctor.json")


if __name__ == "__main__":
    main()
