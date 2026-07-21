# xhs_note_reader

`xhs_note_reader` is a local Agent tool for reading public Xiaohongshu notes without browser automation, login state, cookies, private messages, paid content, or official APIs.

It resolves a share URL, reads the public SSR HTML, extracts `window.__INITIAL_STATE__`, normalizes `note.noteDetailMap[noteId].note`, optionally downloads images with `Referer: https://www.xiaohongshu.com/`, and can run OCR.

The default OCR mode is `--ocr-engine auto`: try PaddleOCR first, judge the result with simple quality heuristics, and only fall back to the local MiniCPM-V VLM wrapper when PaddleOCR is unavailable, fails, or looks too poor.

VLM fallback uses:

```text
D:\MyLab\Hugo\bubblevan.github.io\scripts\local-vision\describe-image.ps1
```

## Basic Usage

```powershell
python scripts/tools/xhs_note_reader.py `
  --url "https://www.xiaohongshu.com/discovery/item/<noteId>" `
  --out-json D:\MyLab\xhs-note.json
```

With image OCR:

```powershell
python scripts/tools/xhs_note_reader.py `
  --url "http://xhslink.com/o/xxxx" `
  --ocr-images `
  --ocr-engine auto `
  --max-images 20 `
  --out-json D:\MyLab\xhs-note.json
```

The output is always UTF-8 JSON. If `--out-json` is omitted, JSON is printed to stdout.

## Output Shape

```json
{
  "ok": true,
  "url": "...",
  "final_url": "...",
  "note_id": "...",
  "title": "...",
  "desc": "...",
  "author": {"nickname": "...", "user_id": "..."},
  "tags": [],
  "stats": {"likes": "...", "collects": "...", "comments": "..."},
  "images": [
    {
      "index": 1,
      "url": "...",
      "local_path": "...",
      "ocr": "...",
      "summary": "...",
      "ocr_engine": "paddle|vlm",
      "ocr_confidence": 0.98,
      "ocr_fallback_reason": ""
    }
  ],
  "combined_text": "title + desc + image OCR",
  "errors": []
}
```

Fatal failures return the same shape with `"ok": false`.

## Cache

Images are cached under:

```text
.cache/xhs_note_reader/<noteId>/
```

Cached files are keyed by image URL hash, so repeated runs avoid repeated downloads.

## OCR Engines

PaddleOCR is a Python SDK. Install it in the Python environment that Hermes uses to run this tool, for example:

```powershell
python -m pip install paddleocr
```

Depending on your environment, PaddleOCR may also install or require the matching PaddlePaddle runtime. If PaddleOCR is not importable, `--ocr-engine auto` will record the failure and use VLM fallback.

```powershell
# Default: PaddleOCR first, VLM fallback only when needed.
python scripts/tools/xhs_note_reader.py --url "<url>" --ocr-images --ocr-engine auto

# Force PaddleOCR only.
python scripts/tools/xhs_note_reader.py --url "<url>" --ocr-images --ocr-engine paddle --no-vlm-fallback

# Force MiniCPM-V/VLM OCR.
python scripts/tools/xhs_note_reader.py --url "<url>" --ocr-images --ocr-engine vlm
```

Auto mode accepts PaddleOCR when:

- extracted text length is at least `--paddle-min-chars` (default `20`);
- average confidence is at least `--paddle-min-confidence` (default `0.50`) when confidence is available;
- the text does not contain replacement characters and has a reasonable useful-character ratio.

When auto mode falls back, the image object records `ocr_engine: "vlm"` and `ocr_fallback_reason`, and the top-level `errors` list includes `OCR_FALLBACK[index]`.

PaddleOCR is a Python SDK. It is imported dynamically, so the tool still works without PaddleOCR installed; auto mode will fall back to VLM unless `--no-vlm-fallback` is set.

## Failure Handling

- Short link cannot redirect or fetch: returns `URL_FETCH_FAILED`.
- SSR HTML has no `window.__INITIAL_STATE__`: returns `INITIAL_STATE_NOT_FOUND`.
- Initial state exists but note data is missing: returns `NOTE_NOT_FOUND`.
- Image download fails: appends `IMAGE_DOWNLOAD_FAILED[index]` to `errors` and continues.
- OCR times out: appends `OCR_TIMEOUT[index]` and continues.
- OCR command fails: appends `OCR_FAILED[index]` and continues.
- PaddleOCR unavailable in auto mode: falls back to VLM and records `OCR_FALLBACK[index]`.

There is no infinite retry loop.

## Test Samples

Sample 1: parse a saved SSR HTML fixture successfully.

```powershell
python scripts/tools/xhs_note_reader.py `
  --url "https://www.xiaohongshu.com/discovery/item/abc123" `
  --html-file scripts/tools/fixtures/xhs_initial_state.html `
  --out-json D:\MyLab\xhs-fixture-ok.json
```

Sample 2: verify clear failure when no initial state exists.

```powershell
python scripts/tools/xhs_note_reader.py `
  --url "https://www.xiaohongshu.com/discovery/item/missing" `
  --html-file scripts/tools/fixtures/xhs_no_initial_state.html `
  --out-json D:\MyLab\xhs-fixture-fail.json
```

Run the offline unit tests:

```powershell
python -m unittest scripts.tools.test_xhs_note_reader
```
