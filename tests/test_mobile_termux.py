"""CPU-only tests for mobile parsing; no model, Termux or GPU needed."""
import importlib.util
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError
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


    def test_model_request_keeps_thinking_enabled(self):
        response = io.BytesIO(json.dumps({
            "choices": [{"message": {"content": "43"}}]
        }).encode("utf-8"))
        with patch.object(module, "urlopen", return_value=response) as mocked:
            module.call_model([{"role": "user", "content": "5 * 12 - 17"}])
        request = mocked.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": True})
        self.assertEqual(payload["max_tokens"], 512)
        self.assertFalse(payload["stream"])

    def test_upstream_error_shows_reason_not_request(self):
        message = '{"error":{"code":400,"message":"unsupported template option"}}'
        failure = HTTPError("http://127.0.0.1", 400, "Bad Request", None,
                            io.BytesIO(message.encode()))
        detail = module.upstream_error_detail(failure)
        self.assertEqual(detail, "unsupported template option")

    def test_upstream_error_does_not_reflect_arbitrary_response(self):
        failure = HTTPError("http://127.0.0.1", 500, "Failed", None,
                            io.BytesIO(b"client prompt: personal information"))
        self.assertEqual(module.upstream_error_detail(failure), "llama.cpp HTTP 500")


if __name__ == "__main__":
    unittest.main()
