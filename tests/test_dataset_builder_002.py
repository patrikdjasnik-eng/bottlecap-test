import unittest
from diagnostics.dataset_builder_002 import worklist
from diagnostics.safe_start_plan import SEEDS

def setup():
    q=[{"question_id":f"gsm8k-{i}","question":f"Question {i}?",
         "source":"gsm8k","source_revision":"a"*40,"split":"train","task":"math"}
       for i in range(12)]
    attempts=[{"question_id":x["question_id"],"seed":s} for x in q for s in SEEDS]
    return q,attempts

class DatasetBuilder002Tests(unittest.TestCase):
    def test_full_worklist_is_plan_only(self):
        q,a=setup()
        r=worklist(q,a)
        self.assertEqual(r["question_count"],12)
        self.assertEqual(r["planned_generations"],36)
        self.assertFalse(r["training_authorized"])
        self.assertFalse(r["gpu_used"])
        self.assertFalse(r["questions"][0]["gold_answer_exported"])
    def test_exclude_already_used_question(self):
        q,a=setup()
        r=worklist(q,a,exclude_ids=["gsm8k-0"])
        self.assertEqual(r["question_count"],11)
        self.assertEqual(r["planned_generations"],33)
    def test_unknown_exclusion_fails(self):
        q,a=setup()
        with self.assertRaises(ValueError):worklist(q,a,exclude_ids=["unknown"])
    def test_duplicate_seed_fails(self):
        q,a=setup()
        a[1]["seed"]=a[0]["seed"]
        with self.assertRaises(ValueError):worklist(q,a)
    def test_duplicate_exclusion_fails(self):
        q,a=setup()
        with self.assertRaises(ValueError):worklist(q,a,exclude_ids=["gsm8k-0","gsm8k-0"])

if __name__=="__main__":
    unittest.main()
