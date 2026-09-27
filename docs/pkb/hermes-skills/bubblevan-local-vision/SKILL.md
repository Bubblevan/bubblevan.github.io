---
name: bubblevan-local-vision
description: Use the local MiniCPM-V llama.cpp CLI wrapper for explicitly requested offline image analysis when the active agent cannot inspect the image directly.
version: 1.0.0
metadata:
  required_tools: [terminal]
  related_skills: [bubblevan-pkb-capture, bubblevan-hugo-site]
---

# Bubblevan Local Vision

Use this skill only when the user specifically requests local/offline image processing or the active agent cannot inspect the image. For ordinary image reading and summaries, use the active agent's multimodal vision directly.

For Xiaohongshu links, use the `xhs-note-reader` skill to retrieve the anonymously visible note and images, then inspect those images with the active agent's multimodal vision. Do not run PaddleOCR or this local wrapper as an intermediate step.

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
- Do not use this as an automatic fallback from ordinary agent image analysis or the Xiaohongshu public note workflow.

## Capture Integration

If the user wants to save the result, first summarize the local vision output, then use `bubblevan-pkb-capture`:

```powershell
python -m scripts.pkb.cli capture --type note --text "<summary>" --visibility private --source-agent hermes --source-platform windows --source-channel wechat --raw "<original user message plus image reference>"
```
