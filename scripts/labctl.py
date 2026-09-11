#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "state" / "progress.json"


def load() -> dict:
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    PROGRESS.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    set_p = sub.add_parser("set")
    set_p.add_argument("phase")
    set_p.add_argument("profile")
    set_p.add_argument("state")
    complete = sub.add_parser("complete")
    complete.add_argument("phase")
    complete.add_argument("profile")
    args = parser.parse_args()

    data = load()
    if args.command == "status":
        for phase, profiles in data["phases"].items():
            print(f"Phase {phase}: " + ", ".join(f"{k}={v}" for k, v in profiles.items()))
        return

    phase = str(args.phase)
    if phase not in data["phases"] or args.profile not in data["phases"][phase]:
        raise SystemExit("Unknown phase/profile")
    if args.command == "set":
        data["phases"][phase][args.profile] = args.state
    else:
        data["phases"][phase][args.profile] = "PASS_QUICK" if args.profile == "quick" else "PASS_TEACHING"
    save(data)


if __name__ == "__main__":
    main()
