"""CPU-only tests for mobile parsing; no model, Termux or GPU needed."""
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "mobile" / "termux" / "app.py"
spec = importlib.util.spec_from_file_location("mobile_bottlecap_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MobileChatTest(unittest.TestCase):
    def test_extract_usage_and_timings(self):
        result = module.extract({
            "choices": [{"message": {"content": "43"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "timings": {"predicted_ms": 2000, "prompt_ms": 500}
        })
        self.assertEqual(result["answer"], "43")
        self.assertEqual(result["metrics"]["generatedTokens"], 20)
        self.assertEqual(result["metrics"]["tokensPerSecond"], 10)
        self.assertEqual(result["metrics"]["finishReason"], "stop")

    def test_extract_thinking_markup(self):
        result = module.extract({
            "choices": [{"message": {"content": "<think>5*12=60</think>43"}}]
        })
        self.assertEqual(result["answer"], "43")
        self.assertEqual(result["reasoning"], "5*12=60")
        self.assertIsNone(result["metrics"]["generatedTokens"])

    def test_missing_metrics_are_unknown(self):
        result = module.extract({"choices": [{"message": {"content": "test"}}]})
        self.assertIsNone(result["metrics"]["reasoningTokens"])
        self.assertIsNone(result["metrics"]["generationSeconds"])


if __name__ == "__main__":
    unittest.main()
