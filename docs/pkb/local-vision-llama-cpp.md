# Local Vision With llama.cpp

Bubblevan keeps DeepSeek as the main Hermes reasoning model and uses MiniCPM-V through `llama-cli.exe` only when a text-only model cannot read image content.

This path intentionally avoids `llama-cpp-python`, FastAPI, uvicorn, SGLang, and any OpenAI-compatible localhost service. The Python server path previously hit low-level address/runtime issues, so it is not part of the supported workflow.

## Files

```text
Model:
D:\MyLab\Hugo\MiniCPM-V-4_5\ggml-model-Q8_0.gguf

MMProj:
D:\MyLab\Hugo\MiniCPM-V-4_5\mmproj-model-f16.gguf

llama-cli:
C:\Users\bubblevan\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-cli.exe

Wrapper:
D:\MyLab\Hugo\bubblevan.github.io\scripts\local-vision\describe-image.ps1
```

## Command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "D:\MyLab\Hugo\bubblevan.github.io\scripts\local-vision\describe-image.ps1" `
  -ImagePath "D:\MyLab\Hugo\bubblevan.github.io\content\blog\2026\image.png"
```

The wrapper sets the console to UTF-8 (`chcp 65001`, `InputEncoding`, `OutputEncoding`) before calling `llama-cli`. If output still appears garbled in an already-open terminal, run these once before invoking the wrapper:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
```

## Defaults

- Context: `4096`
- GPU layers: `99`
- Max tokens: `10240`
- Output sections: `### OCR`, `### Image Understanding`, `### Summary`
- Prompt behavior: do OCR and image understanding together, preserve visible structure, mark uncertain text with `[uncertain]`, and avoid reasoning output.

The larger token budget is for Xiaohongshu-style long image posts where the actual content is embedded in screenshots or image cards.

## Hermes Policy

Hermes should call the wrapper only when needed:

- The shared content is image-first.
- A Xiaohongshu, Bilibili, Zhihu, WeChat, or screenshot item has important text inside images.
- The user explicitly asks to read, OCR, or summarize an image.
- The page text is available but the core information is in image cards.

Hermes must not start a long-running vision server by default. For local vision, use the wrapper and let `llama-cli` exit after the task.

## Unsupported Paths

Do not use:

- `python -m sglang.launch_server`
- `llama-cpp-python`
- FastAPI or uvicorn wrappers
- `http://127.0.0.1:30000/v1/chat/completions`
- Any always-on local vision service unless the user explicitly asks for a new server-mode design.
