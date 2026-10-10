import unittest
from diagnostics.rhar_validation_compare import pick_validation,summarize
class ValidationCompareTests(unittest.TestCase):
    def test_disjoint_reproducible_validation(self):
        raw=[{"question":f"Worker {i} packs exactly two boxes. How many boxes?",
              "answer":"Two boxes in total.\n#### 2"} for i in range(120)]
        a=pick_validation(raw,80,20,42,7)
        b=pick_validation(raw,80,20,42,7)
        self.assertEqual(a,b)
        self.assertEqual(len({x["question_id"] for x in a}),7)
    def test_metrics(self):
        records=[{"variant":"sft","id":"a","correct":True,"truncated":False,"tokens":10},
                 {"variant":"cep","id":"a","correct":False,"truncated":False,"tokens":8},
                 {"variant":"sft","id":"b","correct":False,"truncated":True,"tokens":20},
                 {"variant":"cep","id":"b","correct":True,"truncated":False,"tokens":12}]
        x=summarize(records)
        self.assertEqual(x["sft"]["mean_tokens"],15)
        self.assertEqual(x["cep"]["mean_tokens"],10)
        self.assertEqual(x["correctness_delta_cep_minus_sft"],0)
    def test_reject_unpaired(self):
        with self.assertRaises(ValueError):summarize([{"variant":"sft","id":"a"},{"variant":"cep","id":"b"}])
if __name__=="__main__":unittest.main()
