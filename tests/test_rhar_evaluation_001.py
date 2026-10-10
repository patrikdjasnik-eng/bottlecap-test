"""CPU-only checks of exploratory paired evaluation gates."""
import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import rhar_evaluation_001 as e

class PairedEvaluationTests(unittest.TestCase):
    def test_plan_held_out(self):
        p=e.make_plan(Path("adapter"),2)
        self.assertEqual(p["planned_generations"],2)
        self.assertFalse(p["official_benchmark"])
        self.assertFalse(p["training_data_allowed"])
        self.assertTrue(p["thinking_enabled"])
    def test_reject_bad_task(self):
        with self.assertRaises(ValueError):
            e.make_plan(Path("adapter"),7)
    def test_dry_run_no_gpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(e,"execute",side_effect=AssertionError("GPU forbidden")):
                with contextlib.redirect_stdout(StringIO()) as captured:
                    e.main(["--dry-run","--adapter","unused","--out",str(Path(tmp)/"unused")])
            self.assertEqual(json.loads(captured.getvalue())["planned_generations"],2)
    def test_gpu_requires_approval(self):
        for args in (["--execute"],["--dry-run","--approve-gpu-2"]):
            with contextlib.redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    e.main(args+["--adapter","unused","--out","unused"])
    def test_summary_strict(self):
        data=[{"variant":variant,"task_id":"x","seed":9001,"budget":512,
               "total_generated_tokens":tokens,"correct":correct,"truncated":not correct}
              for variant,tokens,correct in (("base",512,False),("adapter",256,True))]
        summary=e.summarize(data)
        self.assertEqual(summary["token_reduction_pct"],50)
        self.assertFalse(summary["quality_preservation_demonstrated"])
        with self.assertRaises(ValueError):e.summarize(data[::-1])

if __name__=="__main__":
    unittest.main()
