import unittest
from diagnostics.training_candidates import select


def record(**extra):
    x={"question_id":"gsm8k-001","source":"gsm8k",
       "prompt":[{"role":"user","content":"2+2?"}],
       "full_generated_text":"<think>2+2 is 4</think>Final answer: 4",
       "total_tokens":25,"correct":True,"truncated":False,
       "split_status":"generated_think_block"}
    x.update(extra)
    return x


class TrainingCandidatesTests(unittest.TestCase):
    def test_choose_shortest_correct(self):
        a=select([record(total_tokens=29),record(total_tokens=15)])
        self.assertEqual(a["selected"][0]["total_tokens"],15)
        self.assertFalse(a["training_performed"])

    def test_accounting_three_generations(self):
        report = select([record(total_tokens=512, correct=False, truncated=True),
                         record(total_tokens=433), record(total_tokens=374)])
        self.assertEqual(report["eligible_count"], 2)
        self.assertEqual(report["selected_count"], 1)
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(report["not_selected_longer_count"], 1)

    def test_reject_wrong(self):
        self.assertEqual(select([record(correct=False)])["selected_count"],0)

    def test_reject_truncated(self):
        self.assertEqual(select([record(truncated=True)])["selected_count"],0)

    def test_reject_bad_split(self):
        self.assertEqual(select([record(split_status="missing")])["selected_count"],0)

    def test_eval_contamination(self):
        for source in ("SVAMP","MBPP+","BFCL","IFEval"):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):select([record(source=source)])

    def test_conflicting_question(self):
        with self.assertRaises(ValueError):
            select([record(),record(prompt=[{"role":"user","content":"changed"}])])

    def test_conflicting_rejected_prompt(self):
        with self.assertRaises(ValueError):
            select([record(correct=False), record(prompt=[{"role":"user","content":"changed"}])])

    def test_missing_fields(self):
        r=record();del r["correct"]
        with self.assertRaises(ValueError): select([r])

    def test_different_questions(self):
        a=select([record(),record(question_id="gsm8k-002")])
        self.assertEqual(a["selected_count"],2)


if __name__=="__main__":
    unittest.main()
