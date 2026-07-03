from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cst_parameter_sweep import _copy_project_bundle, build_sweep_cases, parse_sweep_values, preview_sweep


class CSTParameterSweepTests(unittest.TestCase):
    def test_parse_comma_values(self):
        self.assertEqual(parse_sweep_values("1, 2.5, width/2"), [1, 2.5, "width/2"])

    def test_parse_range_values(self):
        self.assertEqual(parse_sweep_values("1:2:0.5"), [1, 1.5, 2])

    def test_build_cartesian_cases(self):
        cases = build_sweep_cases({"w": "1,2", "h": [10, 20]})

        self.assertEqual(
            cases,
            [
                {"w": 1, "h": 10},
                {"w": 1, "h": 20},
                {"w": 2, "h": 10},
                {"w": 2, "h": 20},
            ],
        )

    def test_build_zip_cases(self):
        cases = build_sweep_cases({"w": [1, 2, 3], "h": [10, 20]}, mode="zip")

        self.assertEqual(cases, [{"w": 1, "h": 10}, {"w": 2, "h": 20}])

    def test_preview_enforces_max_cases(self):
        with self.assertRaises(ValueError):
            preview_sweep({"w": "1,2,3", "h": "1,2,3"}, max_cases=5)

    def test_copy_project_bundle_copies_companion_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "base.cst"
            source.write_text("project", encoding="utf-8")
            companion = root / "base"
            companion.mkdir()
            (companion / "Model").mkdir()
            (companion / "Model" / "Parameters.json").write_text("{}", encoding="utf-8")

            target = root / "out" / "case.cst"
            _copy_project_bundle(source, target, overwrite=False)

            self.assertEqual(target.read_text(encoding="utf-8"), "project")
            self.assertTrue((root / "out" / "case" / "Model" / "Parameters.json").is_file())


if __name__ == "__main__":
    unittest.main()
