from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chemagent.rag import build_index, grounded_context, search


class RetrievalTests(unittest.TestCase):
    def test_build_search_and_grounded_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "documents.jsonl"
            document = {
                "record_id": "mdlab:test:1",
                "title": "Molecular dynamics evidence",
                "text": "Independent replicas are needed for uncertainty estimates.",
                "citation": "MD Learning Lab test",
                "source_ids": ["mdlab_local"],
                "license": "MIT",
            }
            source.write_text(json.dumps(document) + "\n", encoding="utf-8")
            index = root / "index.sqlite"
            self.assertEqual(build_index(source, index), 1)
            hits = search(index, "replicas uncertainty")
            self.assertEqual(hits[0]["record_id"], "mdlab:test:1")
            prompt = grounded_context("What evidence is needed?", hits)
            self.assertIn("[mdlab:test:1]", prompt)
            self.assertIn("Do not invent numerical results", prompt)


if __name__ == "__main__":
    unittest.main()

