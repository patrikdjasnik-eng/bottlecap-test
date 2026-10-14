# BottleCap RHAR · Mobile Research Chat

Experimental Termux UI for the **same Qwen3-0.6B base model** used in BottleCapAI research. Branch-only prototype, no changes to official evaluation, training, or base branch.

## Termux prerequisites

Install a maintained Termux release. In Termux:

~~~sh
pkg update
pkg install python git cmake clang make
~~~

Build llama.cpp from its official source (version/pin should be recorded for reproducible tests):

~~~sh
git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp
cmake -S ~/llama.cpp -B ~/llama.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build ~/llama.cpp/build -j 4 --target llama-server
~~~

Obtain a **Qwen3-0.6B GGUF** matching the research base revision, verify provenance and checksum, and place it at `~/models/qwen3-0.6b.gguf`. Do not confuse a community GGUF with the official base checkpoint.

Terminal session 1:

~~~sh
~/llama.cpp/build/bin/llama-server -m ~/models/qwen3-0.6b.gguf -c 2048 -t 4 --host 127.0.0.1 --port 8080
~~~

Terminal session 2, from the project checkout:

~~~sh
python mobile/termux/app.py
~~~

Open `http://127.0.0.1:8765` in the phone's browser. No cloud and no API key required.

## Research safeguards

- API proxy and UI bind to loopback only. Never forward these ports to the public internet.
- Only summary timing/token metrics are saved to `mobile/termux/runs/metrics.jsonl`; chat messages are not persisted.
- The UI shows N/A for metrics unsupported by the selected llama.cpp version, especially exact reasoning token counts.
- Thinking is requested in the chat template; verify with your llama.cpp build that it is honored.
- Chat carries at most 20 recent user/assistant messages. Server accepts no more than 32 messages per call and caps generation at 512 tokens.
- Mobile GGUF/llama.cpp measurements are **exploratory**. They cannot substitute official Transformers/vLLM BottleCapAI evaluation or prove CEP improvement.
- Phone CPU inference does not train weights. PC performs controlled LoRA experiments, then a selected checkpoint may be exported and measured here.
- New unverified GGUF files are never executed as code, but their origin and hash still require review.

## Next milestones

Pin GGUF provenance, add parser and HTTP tests, compare outputs of frozen checkpoints with consistent prompts/seeds, and record hardware/build metadata for every run.
