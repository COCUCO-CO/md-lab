from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chemagent.config import ConfigError
from chemagent.records import build_sft


def _record(record_id: str, group: str, split: str, **updates: object) -> dict[str, object]:
    record: dict[str, object] = {
        "record_id": record_id,
        "task": "scientific_method",
        "messages": [
            {"role": "user", "content": "What supports this claim?"},
            {"role": "assistant", "content": "A cited calculation or observation."},
        ],
        "source_ids": ["mdlab_local"],
        "license": "MIT",
        "license_evidence": "https://opensource.org/license/mit",
        "evidence": ["mdlab:test-evidence"],
        "attribution": "MD Learning Lab authors",
        "split_group": group,
        "split": split,
        "observation_kind": "didactic",
        "procedural": False,
        "safety_tags": [],
    }
    record.update(updates)
    return record


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


class RecordTests(unittest.TestCase):
    def test_builds_grouped_splits_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "records.jsonl"
            output = root / "sft"
            _write_jsonl(
                input_path,
                [
                    _record("r1", "g1", "train"),
                    _record("r2", "g1", "train"),
                    _record("r3", "g2", "validation"),
                    _record("r4", "g3", "test"),
                ],
            )
            summary = build_sft(input_path, output)
            self.assertEqual(summary.counts, {"train": 2, "validation": 1, "test": 1})
            self.assertTrue((output / "audit.json").is_file())
            built = json.loads((output / "train.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertRegex(built["content_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_group_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "records.jsonl"
            _write_jsonl(
                input_path,
                [_record("r1", "same", "train"), _record("r2", "same", "test")],
            )
            with self.assertRaisesRegex(ConfigError, "leaks"):
                build_sft(input_path, root / "sft")

    def test_rejects_blocked_procedural_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "records.jsonl"
            _write_jsonl(
                input_path,
                [
                    _record(
                        "r1",
                        "g1",
                        "train",
                        procedural=True,
                        safety_tags=["chemical_warfare"],
                    )
                ],
            )
            with self.assertRaisesRegex(ConfigError, "blocked procedural"):
                build_sft(input_path, root / "sft")

    def test_rejects_benchmark_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "records.jsonl"
            _write_jsonl(
                input_path,
                [
                    _record(
                        "r1",
                        "g1",
                        "train",
                        source_ids=["choriso"],
                        license="CC-BY-4.0",
                        attribution="CHORISO authors",
                    )
                ],
            )
            with self.assertRaisesRegex(ConfigError, "benchmark-only"):
                build_sft(input_path, root / "sft")


if __name__ == "__main__":
    unittest.main()

