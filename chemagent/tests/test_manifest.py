from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from chemagent.config import ConfigError
from chemagent.manifest import register_local_file


class ManifestTests(unittest.TestCase):
    def test_registers_hash_without_copying_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "reaction.json"
            artifact.write_bytes(b'{"reaction": "test"}\n')
            output = root / "manifests"
            path, manifest = register_local_file(
                artifact,
                "ord",
                "training",
                "CC-BY-SA-4.0",
                "https://github.com/Open-Reaction-Database/ord-data",
                output,
            )
            expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
            self.assertEqual(manifest["sha256"], expected)
            self.assertTrue(path.is_file())
            self.assertEqual(artifact.read_bytes(), b'{"reaction": "test"}\n')

    def test_rejects_benchmark_registration_for_training(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "benchmark.json"
            artifact.write_text("{}", encoding="utf-8")
            with self.assertRaises(ConfigError):
                register_local_file(
                    artifact,
                    "choriso",
                    "training",
                    "CC-BY-4.0",
                    "https://figshare.com/",
                    Path(directory) / "manifests",
                )


if __name__ == "__main__":
    unittest.main()

