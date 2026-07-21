---
name: xhs-comment-reader
description: Use Bubblevan's local Playwright-based xhs_comment_reader tool to collect visible public Xiaohongshu note comments into UTF-8 JSON for Agent summarization or capture.
version: 1.0.0
metadata:
  required_tools: [terminal, playwright]
  related_skills: [xhs-note-reader, bubblevan-pkb-capture]
---

# xhs_comment_reader

Use this skill only when the user explicitly asks to read, inspect, summarize, save, or analyze comments under a Xiaohongshu note.

For note title, body, author, tags, stats, images, and image OCR, use `xhs-note-reader` first. This comment reader is browser-based and should not be the default path for normal note reading.

## Supported Scope

- Public Xiaohongshu notes opened from `xhslink.com`, `xiaohongshu.com/discovery/item/<noteId>`, or `xiaohongshu.com/explore/<noteId>`.
- Comments and replies that are visible through the user's normal browser session.
- The user's own local Playwright profile at `$HOME\.xhs-playwright-profile`.

## Hard Boundaries

- Do not scrape private messages, paid content, or content behind access controls.
- Do not steal, export, or manually inject cookies.
- Do not bypass Xiaohongshu risk control, CAPTCHA, login walls, or rate limits.
- Do not run this tool in an infinite loop. Respect `--max-seconds` and `--max-scrolls`.
- If no comments are captured, report that honestly and include the output JSON path or error.

## Command

From the repo root:

```powershell
cd D:\MyLab\Hugo\bubblevan.github.io
python scripts/tools/xhs_comment_reader.py `
  --url "<xhs-url>" `
  --out-json "D:\MyLab\xhs-comments.json" `
  --user-data-dir "$HOME\.xhs-playwright-profile" `
  --max-seconds 120 `
  --max-scrolls 40
```

Use `--headless` only when the user has already confirmed the session works without a visible browser.

## Output Contract

The tool writes UTF-8 JSON:

```json
{
  "ok": true,
  "url": "...",
  "comment_count": 0,
  "comments": [],
  "debug": {
    "raw_comment_like_objects": 0
  }
}
```

Each comment may include `comment_id`, `content`, `like_count`, `create_time`, `ip_location`, `user`, `sub_comment_count`, `sub_comment_has_more`, and nested `sub_comments`.

## Recommended Workflow

1. Run `xhs-note-reader` first if the user also needs the note itself.
2. Run `xhs_comment_reader.py` only for the comments layer.
3. Read the JSON and summarize high-signal comments, disagreement, repeated questions, practical tips, and useful user vocabulary.
4. If the user wants to save the result, pass the summary and original URL to `bubblevan-pkb-capture`.

## Failure Handling

- Browser fails to launch: tell the user Playwright/Chromium is unavailable or the profile path is locked.
- Login or CAPTCHA appears: stop and ask the user to handle it manually in the visible browser; do not bypass it.
- `comment_count` is zero: say the page did not expose comment network responses during the bounded scroll window.
- Timeout: surface the timeout and recommend rerunning with a larger `--max-seconds` only if the user wants deeper comment collection.
