import unittest
from diagnostics.stress_trace_analyzer import review, review_record

def row(seed, budget):
    return {"task_id":"rhar003-math-01","seed":seed,"budget":budget,
            "truncated":True,"correct":False,"training_data_allowed":False,
            "generated_text":"<think>28 packs. Wait, wrong! 3/8 is 90, so 20 packs. Check again. Check again."}

class StressTraceTests(unittest.TestCase):
    def test_find_both_numbers_and_correction_cues(self):
        x=review_record(row(9001,512))
        self.assertEqual([v["number"] for v in x["number_mentions"]],["28","20"])
        self.assertTrue(x["possible_answer_revision"])
        self.assertFalse(x["revision_proven"])
        self.assertFalse(x["semantic_reasoning_verified"])
    def test_all_four_required(self):
        data=[row(s,b) for b in (512,1024) for s in (9001,9003)]
        x=review(data)
        self.assertEqual(x["record_count"],4)
        self.assertFalse(x["gpu_used"])
        self.assertFalse(x["training_data_allowed"])
        with self.assertRaises(ValueError):review(data[:3])
    def test_duplicate_rejected(self):
        x=row(9001,512)
        with self.assertRaises(ValueError):review([x,x,x,x])
    def test_foreign_task_rejected(self):
        x=row(9001,512);x["task_id"]="foreign"
        with self.assertRaises(ValueError):review_record(x)
    def test_holdout_gate(self):
        x=row(9001,512);x["training_data_allowed"]=True
        with self.assertRaises(ValueError):review_record(x)

if __name__=="__main__":
    unittest.main()
