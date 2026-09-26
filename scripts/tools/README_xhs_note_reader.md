# Anonymous Xiaohongshu readers

This tool extracts information that Xiaohongshu already exposes on a public note page, without signing in or reusing a browser profile. It first tries ordinary public HTML. When that response is only a login shell, it can open the link in an isolated temporary Chrome profile and read the rendered page through Chrome DevTools Protocol (CDP). It does not use Playwright, extensions, account cookies, or private XHS API endpoints.

## Read a note and download its public images

From the repository root:

~~~powershell
python scripts/tools/xhs_note_reader.py --url "https://www.xiaohongshu.com/explore/<noteId>?xsec_token=..." --download-images --out-json ".cache/xhs-extracted/note.json"
~~~

The program uses the installed Chrome executable and the existing Python websocket-client package for the isolated rendered-page fallback. The temporary Chrome profile is deleted after the run. Add --headless to hide the temporary window. Use --no-browser-fallback to restrict a run to static HTML.

It reads the note title, body, author, tags, visible engagement counts, timestamp, location, image metadata and URLs, plus comments already exposed in the anonymous page. By default, `--max-images 0` keeps the full gallery; a positive value limits it and adds an `IMAGE_LIMIT_APPLIED` warning. The `gallery` object reports available, selected, and truncated image counts. Downloaded image paths are written to `images[*].local_path`. Open every downloaded image with the agent's multimodal image input to read and summarize the whole carousel; this tool does not run OCR.

## Output and limits

The output is UTF-8 JSON. Sensitive query values such as xsec_token are redacted in saved note URLs. Important fields include:

- retrieval.mode: public_ssr_html or isolated_anonymous_chrome_cdp.
- images: carousel order, dimensions, available image variants, and local paths when downloaded.
- gallery: image counts and whether a requested image cap truncated the gallery.
- comments and comments_text: only comments visible in the public anonymous page.
- comments_truncated_by_login: true when the page indicates that more comments require login.
- warnings and errors: static-page limitations and per-image download failures.

A page may expose fewer comments than its displayed total. Do not try to get content behind login, CAPTCHA, paid access, or other restrictions. Report the limit as returned.

If a note's public URL returns an error such as `300011`, a login/security page, or no note data, record that note as inaccessible and stop attempts for it. Do not retry by changing identity, IP, browser profile, token, or endpoint. Do not treat the profile-card cover as the complete gallery or as a complete source harvest. When the user supplies individual note URLs, read those URLs with the note reader; the profile reader alone only describes the anonymous cards it actually rendered.

## Read an author profile and its visible post cards

~~~powershell
@'
from scripts.tools.xhs_profile_reader import main
raise SystemExit(main())
'@ | python - --url 'https://www.xiaohongshu.com/user/profile/<userId>?xsec_token=...' --out-json '.cache/xhs-extracted/profile.json'
~~~

The profile reader uses the same isolated anonymous Chrome/CDP setup. The stdin form shown above is reliable in Codex-hosted Windows runs; the direct `python scripts/tools/xhs_profile_reader.py ...` entry point is also available in ordinary shells. It dismisses the page's visible login dialog through its normal close control, then performs a small bounded number of ordinary page scrolls. The JSON contains public profile fields, aggregate counts, visible post-card titles/timestamps/engagement counts, and cover-image URLs. Share tokens are redacted from the saved source URL.

The profile may report a larger lifetime post count than it renders anonymously. Some anonymous profile cards omit their note ID and link to only the generic `/explore/` route. In that case, the reader records the metadata and cover but does not try to recover an ID, call private endpoints, or open login-gated full text/galleries. The result's `limitations`, `pagination`, and `result` fields describe this boundary. `--scroll-steps` defaults to 4 and is clamped to 0–10.

## Other entry point

scripts/tools/xhs_comment_reader.py remains a compatibility wrapper for older comment commands. `scripts/tools/profile_capture.py` is now a compatibility entry point for `xhs_profile_reader.py`; it no longer prompts for login, uses Playwright, reuses a browser profile, or intercepts XHS endpoints.

For parsing an already saved HTML snapshot without starting Chrome:

~~~powershell
python scripts/tools/xhs_note_reader.py --url "https://www.xiaohongshu.com/explore/<noteId>" --html-file ".cache/xhs-page.html" --out-json ".cache/xhs-extracted/note.json"
~~~
