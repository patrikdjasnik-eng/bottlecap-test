import unittest
from unittest.mock import Mock
from diagnostics.rhar_teacher_train_002 import prepare,encode_teacher
from diagnostics.safe_start_data import DATASET_REVISION
class TeacherTrainTests(unittest.TestCase):
    def q(self):
        return {"question_id":"gsm8k-train-00000","question":"How many apples?",
                "gold_answer":"7","source":"gsm8k","source_revision":DATASET_REVISION,
                "split":"train"}
    def row(self):
        return {"question":"How many apples?","answer":"3 + 4 = <<3+4=7>>7.\n#### 7"}
    def test_reference_correct_and_thinking_terminates(self):
        x=prepare([self.q()],[self.row()])[0]
        self.assertIn("</think>\nFinal answer: 7",x["completion"])
        self.assertNotIn("<<",x["completion"])
        self.assertTrue(x["reference_solution"])
    def test_source_gold_mismatch_rejected(self):
        row=self.row();row["answer"]="#### 8"
        with self.assertRaises(ValueError):prepare([self.q()],[row])
    def test_excludes_used(self):
        with self.assertRaises(ValueError):prepare([self.q()],[self.row()],["gsm8k-train-00000"])
    def test_unapproved_source_rejected(self):
        q=self.q();q["split"]="test"
        with self.assertRaises(ValueError):prepare([q],[self.row()])
    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):prepare([self.q()],[self.row()],["unknown"])
if __name__=="__main__":
    unittest.main()
