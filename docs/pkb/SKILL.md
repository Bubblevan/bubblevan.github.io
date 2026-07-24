# Hermes Adapter Guide

Hermes runtime config and installed skills live outside this repository:

```text
C:\Users\bubblevan\AppData\Local\hermes
```

This repository stores project-side guidance only. Do not create repo-local Hermes runtime config under `.hermes/`.

## Capture

For note, link, task, event, bookmark, and project-log capture intents, Hermes should use:

```powershell
cd D:\MyLab\Hugo\bubblevan.github.io
python -m scripts.pkb.cli capture --type note --text "<summary>" --visibility private --source-agent hermes --source-platform windows --source-channel desktop --raw "<verbatim user message>"
```

Do not directly edit `content/` or official `data/*.yaml` during capture.

## Local Vision

For image-first content, use the installed `bubblevan-local-vision` skill and the repo wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "D:\MyLab\Hugo\bubblevan.github.io\scripts\local-vision\describe-image.ps1" `
  -ImagePath "<absolute-image-path>"
```

This is the only supported local vision path. Do not use Python FastAPI, `llama-cpp-python`, SGLang, or `127.0.0.1:30000` for Bubblevan local vision.
