import unittest
from diagnostics.training_002_preflight import audit

def row(i):
    return {"question_id":f"gsm8k-{i}","source":"gsm8k",
            "prompt":[{"role":"user","content":f"Question {i}?"}],
            "completion":"<think>Calculation.</think>\nFinal answer: 2","total_tokens":20}
def data(rows):
    return {"status":"training_data_candidates_only","selected_count":len(rows),"selected":rows}
class Training002PreflightTests(unittest.TestCase):
    def test_one_sample_blocked(self):
        self.assertEqual(audit(data([row(1)]))["status"],"blocked")
    def test_eight_distinct_pass_structural_gate_only(self):
        result=audit(data([row(i) for i in range(8)]))
        self.assertEqual(result["status"],"candidate_gate_passed_manual_review_required")
        self.assertFalse(result["training_authorized"])
    def test_duplicate_prompt_blocked(self):
        rows=[row(i) for i in range(8)]
        rows[2]["prompt"]=rows[1]["prompt"]
        self.assertEqual(audit(data(rows))["status"],"blocked")
    def test_holdout_source_blocked(self):
        rows=[row(i) for i in range(8)]
        rows[1]["source"]="rhar003-math-01"
        self.assertEqual(audit(data(rows))["status"],"blocked")
    def test_missing_final_blocked(self):
        rows=[row(i) for i in range(8)]
        rows[1]["completion"]="<think>Only reasoning</think>"
        self.assertEqual(audit(data(rows))["status"],"blocked")
if __name__=="__main__":
    unittest.main()
