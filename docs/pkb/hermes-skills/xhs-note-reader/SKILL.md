---
name: xhs-note-reader
description: Use Bubblevan's local Xiaohongshu tools to extract public note metadata/images with xhs_note_reader and perform fast batch image OCR with extract_paddleocr.py in the paddle3.7 environment for Agent summarization.
version: 1.0.0
metadata:
  required_tools: [terminal]
  related_skills: [bubblevan-local-vision, bubblevan-pkb-capture]
---

# xhs_note_reader

Use this skill when the user sends a Xiaohongshu or xhslink URL and asks Hermes to read, summarize, save, or inspect the note.

## Supported Scope

- Public Xiaohongshu share links.
- `xhslink.com/o/...` short links that redirect through normal HTTP.
- `xiaohongshu.com/discovery/item/<noteId>` links.
- `xiaohongshu.com/explore/<noteId>` links.

## Hard Boundaries

- Do not use login state, cookies, private messages, paid content, or simulated user accounts.
- Do not use browser automation by default.
- Do not call Xiaohongshu official APIs.
- Do not retry forever. If SSR HTML has no `window.__INITIAL_STATE__`, report the JSON error.
- Default OCR is PaddleOCR-only on Bubblevan's laptop. Prefer `scripts/tools/extract_paddleocr.py` in the `paddle3.7` environment for downloaded image folders.
- Do not call the MiniCPM-V / llama.cpp VLM fallback automatically. It can make the laptop unusable during model loading.
- If PaddleOCR fails or looks low quality, report the OCR issue and ask before using `bubblevan-local-vision`.
- If the user explicitly approves VLM fallback, use only `scripts/local-vision/describe-image.ps1` through the tool.
- Do not use Python FastAPI, `llama-cpp-python`, SGLang, or `127.0.0.1:30000`.

## Command

Metadata only, from the repo root:

```powershell
cd D:\MyLab\Hugo\bubblevan.github.io
python scripts/tools/xhs_note_reader.py --url "<xhs-url>" --out-json "D:\MyLab\xhs-note.json"
```

Download images without OCR:

```powershell
python scripts/tools/xhs_note_reader.py --url "<xhs-url>" --download-images --max-images 20 --out-json "D:\MyLab\xhs-note.json"
```

Batch OCR for a folder of downloaded images:

```powershell
D:\Anaconda\envs\paddle3.7\python.exe D:\MyLab\Hugo\bubblevan.github.io\scripts\tools\extract_paddleocr.py "D:\MyLab\xhs-images" > "D:\MyLab\xhs-ocr.json"
```

If `xhs_note_reader.py --download-images` created a note cache directory such as `.cache\xhs_note_reader\<note_id>`, pass that directory to `extract_paddleocr.py` instead of `D:\MyLab\xhs-images`.

Use `D:\Anaconda\envs\paddle3.7\python.exe` directly for OCR-enabled runs. Do not use `conda run` for OCR output; its Windows console wrapper can fail on mixed UTF-8/GBK output.

## Output Contract

Read the generated UTF-8 JSON and use `combined_text` for downstream summarization. If `ok=false`, surface the first item in `errors` honestly.

Image-level download failures from `xhs_note_reader.py` are stored under `errors` while preserving whatever metadata was extracted.

`extract_paddleocr.py` writes JSON to stdout and progress logs to stderr. The JSON shape is:

```json
{
  "img_01.jpg": ["line 1", "line 2"],
  "img_02.jpg": ["line 1", "line 2"]
}
```

When summarizing, concatenate each image's line list in filename order and combine it with the note title/body from `xhs_note_reader.py`.

Known-good PaddleOCR state on 2026-07-21 in `paddle3.7`:

- `paddleocr.__version__=2.7.0.2`
- `PaddlePaddle=2.5.2`
- `CUDA compiled=True`
- `GPU count=1`
- `OCR device=GPU`
- 11 Xiaohongshu images completed in about 3.84 seconds after about 4.95 seconds initialization.

If Hermes reports old `py312`, PaddleOCR 3.x, oneDNN, PIR, CPU, or `conda run` errors, treat that as stale guidance. Use `D:\Anaconda\envs\paddle3.7\python.exe` plus `extract_paddleocr.py` instead.

## Capture Integration

If the user wants to save the note, summarize the JSON first and then call `bubblevan-pkb-capture`. Preserve the original Xiaohongshu URL in `--url` and the raw user message in `--raw`.
