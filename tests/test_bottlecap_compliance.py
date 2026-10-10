import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.bottlecap_compliance import inspect

class ComplianceTests(unittest.TestCase):
    def test_missing_artifacts_not_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            out=inspect(p/"base",p/"mine",p/"lora",p/"IDEA.md")
            self.assertEqual(out["status"],"incomplete")
            self.assertFalse(out["guarantees_accuracy_or_token_savings"])

    def test_pairing_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name, cohort in [("base","x"),("mine","y")]:
                folder=p/name;folder.mkdir()
                (folder/"results.json").write_text(json.dumps({
                    "selection":"full","cohort_sha256":cohort,"samples":8,"seed":42}))
            (p/"lora").mkdir();(p/"lora"/"adapter_model.safetensors").write_bytes(b"test")
            (p/"IDEA.md").write_text("Method and limitations")
            (p/"bundle").write_bytes(b"x")
            out=inspect(p/"base",p/"mine",p/"lora",p/"IDEA.md",p/"bundle")
            self.assertEqual(out["status"],"incomplete")
            self.assertTrue(any("cohort_sha256" in x for x in out["issues"]))

if __name__=="__main__":
    unittest.main()
