#!/usr/bin/env python3
"""Local-only BottleCap mobile chat bridge for llama.cpp."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MAX_BODY = 65536
LLAMA_PORT = int(os.environ.get("BOTTLECAP_LLAMA_PORT", "8080"))
if not 1024 <= LLAMA_PORT <= 65535:
    raise ValueError("BOTTLECAP_LLAMA_PORT must be between 1024 and 65535")
UPSTREAM = f"http://127.0.0.1:{LLAMA_PORT}/v1/chat/completions"
HEALTH_URL = f"http://127.0.0.1:{LLAMA_PORT}/health"


def upstream_error_detail(exc):
    """Return only llama.cpp's error description, not echoed chat content."""
    try:
        payload = json.loads(exc.read(8192).decode("utf-8", errors="replace"))
        if isinstance(payload, dict):
            error = payload.get("error", payload)
            if isinstance(error, dict):
                description = error.get("message") or error.get("type")
            elif isinstance(error, str):
                description = error
            else:
                description = None
            if isinstance(description, str):
                return description.strip()[:300]
    except (ValueError, UnicodeDecodeError, OSError):
        pass
    return f"llama.cpp HTTP {exc.code}"


LANGUAGE_MODES = {"raw", "cs"}
CZECH_SYSTEM_PROMPT = (
    "You are Qwen3-0.6B in a Czech-language chat experiment. "
    "Understand the user's request and reply naturally in Czech (cs-CZ). "
    "Keep numbers, logical conditions, and facts unchanged. "
    "If you do not understand a Czech question, ask for clarification in Czech "
    "instead of guessing. Keep your final answer clear. "
    "This is not an official model benchmark."
)


def prepare_messages(messages, language_mode="raw"):
    if language_mode not in LANGUAGE_MODES:
        raise ValueError("invalid language mode")
    if language_mode == "raw":
        return list(messages)
    return [{"role": "system", "content": CZECH_SYSTEM_PROMPT}, *messages]


def call_model(messages, timeout=180, language_mode="raw"):
    payload = {
        "messages": prepare_messages(messages, language_mode), "temperature": 0.6, "top_p": 0.95,
        "max_tokens": 512, "stream": False,
        "chat_template_kwargs": {"enable_thinking": True},
    }
    request = Request(
        UPSTREAM, data=json.dumps(payload).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def extract(data):
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if "<think>" in content and "</think>" in content:
        before, tail = content.split("<think>", 1)
        thought, after = tail.split("</think>", 1)
        reasoning = reasoning or thought.strip()
        content = (before + after).strip()
    timings = data.get("timings") or {}
    usage = data.get("usage") or {}
    prompt = usage.get("prompt_tokens", timings.get("prompt_n"))
    completion = usage.get("completion_tokens", timings.get("predicted_n"))
    ms = timings.get("predicted_ms")
    speed = timings.get("predicted_per_second")
    if speed is None and completion and ms:
        speed = round(completion * 1000 / ms, 2)
    return {"answer": content, "reasoning": reasoning, "metrics": {
        "promptTokens": prompt, "generatedTokens": completion,
        "totalTokens": usage.get("total_tokens"),
        "tokensPerSecond": speed,
        "generationSeconds": round(ms / 1000, 3) if ms is not None else None,
        "promptSeconds": round(timings["prompt_ms"] / 1000, 3) if timings.get("prompt_ms") is not None else None,
        "finishReason": choice.get("finish_reason", "unknown"),
        "reasoningTokens": usage.get("reasoning_tokens"),
    }}


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            try:
                with urlopen(HEALTH_URL, timeout=3) as response:
                    state = json.load(response)
                    self.respond(200, {
                        "server": "online", "upstream": response.status,
                        "status": state.get("status", "unknown"),
                        "inferenceVerified": False,
                    })
            except (HTTPError, URLError, TimeoutError, ValueError):
                self.respond(503, {"server": "offline", "inferenceVerified": False})
        else:
            self.respond(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/chat":
            return self.respond(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                return self.respond(413, {"error": "invalid_request_size"})
            request = json.loads(self.rfile.read(length))
            messages = request.get("messages")
            if not isinstance(messages, list) or not 1 <= len(messages) <= 32:
                return self.respond(400, {"error": "invalid_messages"})
            if any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                   or not isinstance(m.get("content"), str) or len(m["content"]) > 8000 for m in messages):
                return self.respond(400, {"error": "invalid_message_content"})
            language_mode = request.get("languageMode", "raw")
            if language_mode not in LANGUAGE_MODES:
                return self.respond(400, {"error": "invalid_language_mode"})
            result = extract(call_model(messages, language_mode=language_mode))
            result["languageMode"] = language_mode
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            result["runtime"] = "llama.cpp / GGUF (unofficial)"
            folder = ROOT / "runs"
            folder.mkdir(exist_ok=True)
            # Store aggregate research data only; never store private chat text by default.
            with (folder / "metrics.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps({"timestamp": result["timestamp"],
                    "runtime": result["runtime"], "languageMode": language_mode,
                    **result["metrics"]}) + "\n")
            self.respond(200, result)
        except HTTPError as exc:
            self.respond(502, {
                "error": "model_request_rejected",
                "upstreamStatus": exc.code,
                "detail": upstream_error_detail(exc),
            })
        except (URLError, TimeoutError) as exc:
            self.respond(502, {
                "error": "model_unavailable",
                "detail": "llama.cpp did not respond. Check llama.stderr.log.",
            })
        except json.JSONDecodeError:
            self.respond(502, {"error": "invalid_model_response", "detail": "llama.cpp returned invalid JSON."})
        except (ValueError, KeyError, TypeError):
            self.respond(400, {"error": "invalid_request"})
        except Exception:
            self.respond(500, {"error": "internal_error", "detail": "Check chat.stderr.log."})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be 1024..65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"BottleCap Mobile Research: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
