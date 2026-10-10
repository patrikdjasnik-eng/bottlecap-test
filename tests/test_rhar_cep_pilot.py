import unittest
from diagnostics.rhar_cep_pilot import anchor_mask

class CEPPilotTests(unittest.TestCase):
    def extract(self,text,question):
        return [text[a:b] for a,b in anchor_mask(text,question)]
    def test_source_number_protected(self):
        s="We have 240 items; three eighths are 90."
        labels=self.extract(s,"There are 240 items in stock.")
        self.assertIn("240",labels)
        self.assertNotIn("90",labels)
    def test_operator_and_relation_protected(self):
        s="240 * 3 / 8 = 90 remaining."
        labels=self.extract(s,"240 items, 3/8 are reserved.")
        self.assertIn("*",labels)
        self.assertIn("/",labels)
        self.assertIn("remaining",labels)
    def test_original_terms_only(self):
        self.assertNotIn("90",self.extract("90", "There are 240 items."))
if __name__=="__main__":
    unittest.main()
