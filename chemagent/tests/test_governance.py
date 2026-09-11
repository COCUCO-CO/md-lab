from __future__ import annotations

import unittest

from chemagent.governance import audit_all


class GovernanceTests(unittest.TestCase):
    def test_real_registries_are_structurally_valid(self) -> None:
        result, bundle = audit_all()
        self.assertEqual(result.errors, [])
        self.assertIn("spice", bundle["sources"])
        self.assertTrue(bundle["sources"]["spice"]["training_allowed"])

    def test_benchmarks_and_books_are_disabled(self) -> None:
        _, bundle = audit_all()
        for source_id in ("choriso", "paroutes", "uspto_50k"):
            self.assertFalse(bundle["sources"][source_id]["training_allowed"])
        self.assertFalse(bundle["books"]["openstax_chemistry_2e"]["training_allowed"])


if __name__ == "__main__":
    unittest.main()

