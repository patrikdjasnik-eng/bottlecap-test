import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.lora_pilot import encode_example, load_candidates, main


class StubTokenizer:
    def apply_chat_template(self, *args, **kwargs):
        return [1, 2, 3]
    def __call__(self, *args, **kwargs):
        return {"input_ids": [4, 5]}


class PilotTests(unittest.TestCase):
    def test_masks_only_prompt(self):
        row={"prompt":[{"role":"user","content":"hello"}],"completion":"answer"}
        x=encode_example(row,StubTokenizer(),64)
        self.assertEqual(x["labels"],[-100,-100,-100,4,5])

    def test_no_silent_truncation(self):
        row={"prompt":[{"role":"user","content":"hello"}],"completion":"answer"}
        with self.assertRaises(ValueError):
            encode_example(row,StubTokenizer(),4)

    def test_dry_run_no_gpu(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"candidates.json"
            p.write_text(json.dumps({"status":"training_data_candidates_only",
                "selected_count":1,"selected":[{"prompt":[{"role":"user","content":"hi"}],
                                                "completion":"hello"}]}))
            self.assertEqual(main(["--candidates",str(p),"--out",str(Path(d)/"model"),
                                   "--dry-run"]),0)
            self.assertFalse((Path(d)/"model").exists())

    def test_no_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"candidates.json"
            p.write_text(json.dumps({"status":"training_data_candidates_only",
                "selected_count":1,"selected":[{"prompt":[{"role":"user","content":"hi"}],
                                                "completion":"hello"}]}))
            with self.assertRaises(SystemExit):
                main(["--candidates",str(p),"--out",str(Path(d)/"model")])

    def test_empty_candidates_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"candidates.json"
            p.write_text('{"status":"training_data_candidates_only","selected_count":0,"selected":[]}')
            with self.assertRaises(ValueError):load_candidates(p)


if __name__=="__main__":
    unittest.main()
