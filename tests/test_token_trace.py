import unittest

from diagnostics.token_trace import build_token_trace, verify_token_trace


class StubTokenizer:
    def decode(self, ids, skip_special_tokens=False):
        return "".join({1: "hi", 2: " ", 3: "there"}[value] for value in ids)


class TokenTraceTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = StubTokenizer()
        self.trace = build_token_trace(
            [1, 2, 3], self.tokenizer, "hi there", model_revision="pinned"
        )

    def test_roundtrip(self):
        self.assertTrue(verify_token_trace(self.trace, self.tokenizer, "hi there"))
        self.assertEqual(self.trace["generated_token_count"], 3)

    def test_original_ids_preserved(self):
        self.assertEqual(self.trace["generated_token_ids"], [1, 2, 3])
        self.assertTrue(self.trace["decode_roundtrip_verified"])

    def test_reject_tampered_ids(self):
        self.trace["generated_token_ids"][1] = 1
        with self.assertRaises(ValueError):
            verify_token_trace(self.trace, self.tokenizer, "hi there")

    def test_reject_wrong_count(self):
        self.trace["generated_token_count"] = 4
        with self.assertRaises(ValueError):
            verify_token_trace(self.trace, self.tokenizer, "hi there")

    def test_reject_bad_text(self):
        with self.assertRaises(ValueError):
            build_token_trace([1], self.tokenizer, "wrong", model_revision="pinned")

    def test_reject_bool_ids(self):
        with self.assertRaises(ValueError):
            build_token_trace([True], self.tokenizer, "hi", model_revision="pinned")

    def test_reject_unknown_schema(self):
        self.trace["schema"] = "unknown"
        with self.assertRaises(ValueError):
            verify_token_trace(self.trace, self.tokenizer, "hi there")

    def test_not_a_savings_claim(self):
        self.assertIsNone(self.trace["measured_token_savings"])
        self.assertFalse(self.trace["early_stop_safety_verified"])


if __name__ == "__main__":
    unittest.main()
