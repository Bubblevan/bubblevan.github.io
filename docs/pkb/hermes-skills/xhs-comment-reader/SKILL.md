---
name: xhs-comment-reader
description: Read and summarize only the comments already visible on a public anonymous Xiaohongshu note page.
version: 2.0.0
metadata:
  required_tools: [terminal]
  related_skills: [xhs-note-reader, bubblevan-pkb-capture]
---

# Xiaohongshu public comments

Comment extraction is part of the shared public note reader. Use the xhs-note-reader skill for both note and comment content.

For callers that still expect the old comments-only JSON shape, use the compatibility wrapper:

~~~powershell
python scripts/tools/xhs_comment_reader.py --url "<xhs-url>" --out-json ".cache/xhs-extracted/comments.json"
~~~

The wrapper reads only comments already available to the anonymous page. It uses the same isolated temporary Chrome profile and never reuses --user-data-dir. When comments_truncated_by_login is true, report the visible subset and the displayed total separately. Never attempt to access login-gated comments.
