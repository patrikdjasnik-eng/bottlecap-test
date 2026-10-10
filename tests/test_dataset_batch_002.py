import unittest
from diagnostics.dataset_batch_002 import batch

def worklist():
    return {"status":"plan_only","gpu_used":False,"training_authorized":False,
            "question_count":4,"questions":[
              {"question_id":f"gsm8k-{n}","source":"gsm8k","split":"train",
               "status":"awaiting_generation_and_independent_grading",
               "generation_attempts":3,"seeds":[9001,9002,9003],
               "prompt_sha256":str(n)*64,"gold_answer_exported":False,
               "question_text_exported":False} for n in range(4)]}
class BatchTests(unittest.TestCase):
    def test_two_questions_six_planned(self):
        x=batch(worklist())
        self.assertEqual(x["planned_generations"],6)
        self.assertFalse(x["gpu_used"])
        self.assertEqual(x["model_generations_performed"],0)
    def test_page(self):
        self.assertEqual(batch(worklist(),size=1,start=2)["question_ids"],["gsm8k-2"])
    def test_invalid_size(self):
        with self.assertRaises(ValueError):batch(worklist(),size=4)
    def test_duplicate_rejected(self):
        w=worklist();w["questions"][1]["question_id"]=w["questions"][0]["question_id"]
        with self.assertRaises(ValueError):batch(w)
    def test_provenance_rejected(self):
        w=worklist();w["questions"][0]["split"]="test"
        with self.assertRaises(ValueError):batch(w)
    def test_no_inference_or_training_gate(self):
        w=worklist();w["training_authorized"]=True
        with self.assertRaises(ValueError):batch(w)
if __name__=="__main__":
    unittest.main()
