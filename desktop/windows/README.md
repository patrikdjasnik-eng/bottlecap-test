# BottleCap RHAR Chat — Windows PowerShell prototype

Run the **same Qwen3-0.6B** used by BottleCap research through a private local BottleCap web chat on Windows 10 x64. This is an additional launch target for the existing HTML/Python UI in mobile/termux, not another model or research branch.

## Requirements

- Windows 10 x64 (PowerShell 5.1 or newer)
- Working Python 3 in PATH (python --version)
- Git (for checking out the repository)
- Internet access for first install only; no administrator privileges required

## Start

In Windows PowerShell:

~~~powershell
cd $HOME\Desktop
git clone -b feat/termux-qwen-research-chat https://github.com/patrikdjasnik-eng/bottlecap-test.git bottlecap-powershell
cd .\bottlecap-powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\desktop\windows\Start-BottleCap.ps1
~~~

The script downloads the **official pinned llama.cpp b11414 Windows CPU x64 release** (~19 MB) and **ggml-org/Qwen3-0.6B Q4_0 GGUF** (~429 MB), checks SHA-256 before use, and starts:

- Qwen3-0.6B llama.cpp API on 127.0.0.1:18080 (separate from port 8080)
- Existing BottleCap web chat on http://127.0.0.1:8765

Open the chat address in a browser. The launcher exits after both services become ready; servers continue running until explicitly stopped or the PC restarts.

On later runs, reuse the same launcher. Files are cached in %LOCALAPPDATA%\BottleCapRHAR, and their hashes are checked before launch. The launcher fails rather than silently connecting to an unknown model or service already using a port.

## Stop

From the repository directory:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\desktop\windows\Stop-BottleCap.ps1
~~~

Only the PIDs recorded on successful launch are candidates for termination. Each process is checked against its original command line/path before stopping. If something fails, inspect %LOCALAPPDATA%\BottleCapRHAR\*.log.

## Research and security notes

- The only base model is **Qwen3-0.6B**; Q4_0 is a quantization for exploratory inference.
- This Windows v0.1 launcher is **CPU-only**, even if a GPU is available. CUDA acceleration can be added separately after validating the baseline.
- Thinking is requested by the Python bridge. Exact reasoning-token counts are reported only if the inference server supplies them; otherwise the UI displays N/A.
- There is no LoRA training in this script, and it does not modify official BottleCapAI evaluation files.
- No external API credentials are used. Both servers bind to 127.0.0.1 only.
- Metrics are written locally to mobile/termux/runs/metrics.jsonl. Chat text is not stored by the backend.
- Runs are **unofficial GGUF/llama.cpp exploratory results**, not official BottleCapAI benchmarks.
- Provenance: llama.cpp b11414, CPU x64 SHA-256 6d665084c3f5c97230a7dffc2cfd03e500f048899f350808c5969d53e4c77493; Qwen3-0.6B Q4_0 SHA-256 da2572f16c06133561ce56accaa822216f2391ef4d37fba427801cd6736417d4.

## Troubleshooting

- **Python not found**: run python --version, install Python 3, and reopen PowerShell.
- **Port 8765 or 18080 occupied**: stop the previous BottleCap instance or identify the other program; the launcher will not replace it.
- **Download/checksum failure**: do not disable hash verification. Inspect the error and retry.
- **Model seems slow**: this is expected for the initial CPU version, particularly on older processors.
