---
name: xhs-comment-reader
description: Read comments already rendered on a Xiaohongshu note in the user's existing Chrome profile through chrome-use.
version: 3.0.0
metadata:
  required_tools: [terminal]
  related_skills: [xhs-note-reader, bubblevan-pkb-capture]
---

# Xiaohongshu rendered comments

Use only when the user asks to read or summarize comments. Run from the repository root:

~~~powershell
python scripts/tools/xhs_comment_reader.py --url "<xhs-url>" --out-json ".cache/xhs-extracted/comments.json"
~~~

This compatibility command reads only the comment text already rendered by the user's existing Chrome profile through `chrome-use`. The CLI and profile connection must already be set up. It does not use Playwright, start a new browser/profile, read cookies/storage, expand login-gated sections, or bypass restrictions.

Report `comments_text` as the rendered subset and `comment_count_label` as the displayed total; they are different measurements. If the page returns a login/security wall or CAPTCHA, stop. Do not retry through another identity, IP, token, endpoint, or browser profile.
