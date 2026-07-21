---
name: bubblevan-local-vision
description: Use the local MiniCPM-V llama.cpp CLI wrapper for OCR and image understanding when Hermes or Bubblevan needs to read screenshots, Xiaohongshu image cards, WeChat images, or other image-first content.
version: 1.0.0
metadata:
  required_tools: [terminal]
  related_skills: [bubblevan-pkb-capture, bubblevan-hugo-site]
---

# Bubblevan Local Vision

Use this skill when the user asks Hermes to read, OCR, understand, or summarize an image, screenshot, Xiaohongshu image post, WeChat image, Bilibili screenshot, Zhihu screenshot, or any content whose important information is embedded in images.

For Xiaohongshu links, prefer the `xhs-note-reader` skill first. It extracts note metadata and image URLs, then uses `D:\Anaconda\envs\paddle3.7\python.exe` with `scripts/tools/extract_paddleocr.py` for fast batch OCR.

On Bubblevan's laptop, do not call this local VLM automatically for Xiaohongshu image OCR. MiniCPM-V via llama.cpp can make the machine sluggish while loading. If PaddleOCR fails or the user asks for deeper visual understanding beyond OCR, explain the tradeoff and ask for explicit approval before running this skill.

## Supported Path

Use only the llama.cpp CLI wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "D:\MyLab\Hugo\bubblevan.github.io\scripts\local-vision\describe-image.ps1" `
  -ImagePath "<absolute-image-path>"
```

The wrapper uses:

```text
C:\Users\bubblevan\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-cli.exe
D:\MyLab\Hugo\MiniCPM-V-4_5\ggml-model-Q8_0.gguf
D:\MyLab\Hugo\MiniCPM-V-4_5\mmproj-model-f16.gguf
```

## Task Contract

The local vision result should include:

- OCR: all visible text, preserving structure where possible.
- Image understanding: non-text visual context and what the screenshot/card is showing.
- Summary: a concise Chinese summary of the key information.
- Uncertainty markers: use `[uncertain]` when text is unclear.

## Defaults

- The wrapper sets Windows console encoding to UTF-8 before invoking `llama-cli`.
- Max output tokens default to `10240` for long image posts.
- The model should not output reasoning.
- `llama-cli` should exit after each request.

## Hard Boundaries

- Do not use `llama-cpp-python`.
- Do not use FastAPI or uvicorn wrappers.
- Do not call `http://127.0.0.1:30000/v1/chat/completions`.
- Do not start SGLang.
- Do not keep a local vision server running unless the user explicitly asks for a server-mode redesign.
- Do not run the local vision model just to test availability from Codex; the user validates the CLI in their own PowerShell.
- Do not use this as an automatic fallback from Xiaohongshu OCR on the personal laptop. Prefer reporting the PaddleOCR limitation and asking before loading MiniCPM-V.

## Capture Integration

If the user wants to save the result, first summarize the local vision output, then use `bubblevan-pkb-capture`:

```powershell
python -m scripts.pkb.cli capture --type note --text "<summary>" --visibility private --source-agent hermes --source-platform windows --source-channel wechat --raw "<original user message plus image reference>"
```
