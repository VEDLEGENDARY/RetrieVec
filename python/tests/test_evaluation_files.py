"""Report publication preserves previous results when serialization or replacement fails."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrievec.evaluation.files import validate_outputs, write_json


class EvaluationFilesTests(unittest.TestCase):
    def test_failed_publication_preserves_previous_report_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("previous")
            with patch("retrievec.evaluation.files.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    write_json(path, {"new": True})
            self.assertEqual(path.read_text(), "previous")
            self.assertEqual(list(Path(directory).iterdir()), [path])
            with self.assertRaises(ValueError):
                write_json(path, {"score": float("nan")})
            self.assertEqual(path.read_text(), "previous")

    def test_output_aliases_cannot_overwrite_inputs_or_each_other(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            with self.assertRaises(ValueError):
                validate_outputs([path, path.parent / "." / path.name], [])
            with self.assertRaises(ValueError):
                validate_outputs([path], [path])


if __name__ == "__main__":
    unittest.main()
