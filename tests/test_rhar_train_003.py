import unittest
from diagnostics.rhar_train_003 import prepare_pool,reject_overlap
def examples(n=40):
    return [{"question":f"Shop number {i} sells five apples. How many apples are there?",
             "answer":f"We count five apples in shop {i}.\n#### 5"} for i in range(n)]
class Train003Tests(unittest.TestCase):
    def test_disjoint_reproducible(self):
        train,val=prepare_pool(examples(),20,8,42)
        self.assertEqual(len(train),20)
        self.assertEqual(len(val),8)
        self.assertFalse(set(x["question_id"] for x in train)&set(x["question_id"] for x in val))
        self.assertEqual(train,prepare_pool(examples(),20,8,42)[0])
    def test_short_teacher(self):
        t,v=prepare_pool(examples(),8,8)
        self.assertIn("</think>\nFinal answer: 5",t[0]["completion"])
    def test_eval_overlap_fails(self):
        t,v=prepare_pool(examples(),8,8)
        with self.assertRaises(ValueError):reject_overlap(t,v,[t[0]["question"]])
    def test_no_duplicate_questions(self):
        e=examples();e[5]["question"]=e[0]["question"]
        t,v=prepare_pool(e,20,8)
        self.assertNotEqual(t[0]["question_id"],"unknown")
    def test_insufficient(self):
        with self.assertRaises(ValueError):prepare_pool(examples(10),8,8)
if __name__=="__main__":
    unittest.main()
