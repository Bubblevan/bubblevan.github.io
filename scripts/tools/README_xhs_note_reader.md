# Xiaohongshu reader architecture

The reader separates parsing from acquisition:

- `xhs_note_parser.py` is pure Python. It accepts saved HTML, a Python runtime-state dict, serialized runtime-state JSON, or a sanitized rendered-page snapshot. It does not access the network, filesystem, subprocesses, or browser.
- `xhs_html_acquisition.py` fetches ordinary public HTML and optionally downloads selected image URLs.
- `xhs_chrome_use.py` connects to the user's already-running Chrome through the installed `chrome-use` CLI. It never starts Chrome or a new profile and never reads cookies or browser storage.
- `xhs_note_reader.py` chooses the requested input and applies the parser.

## Static public HTML (default)

```powershell
python scripts/tools/xhs_note_reader.py `
  --url 'https://www.xiaohongshu.com/explore/<noteId>' `
  --download-images `
  --out-json '.cache/xhs-extracted/note.json'
```

Static HTML is the default acquisition. If it contains a usable note, the reader returns that result and makes **zero browser calls**. It does not automatically fall back to any browser. All exposed gallery images are selected by default; a positive `--max-images` sets a cap and records the omitted count and a warning.

## Offline saved HTML and runtime state

Parse a saved HTML document without network access or a browser:

```powershell
python scripts/tools/xhs_note_reader.py `
  --url 'https://www.xiaohongshu.com/explore/<noteId>' `
  --html-file '.cache/xhs-page.html' `
  --out-json '.cache/xhs-extracted/note.json'
```

Parse serialized `window.__INITIAL_STATE__` JSON offline:

```powershell
python scripts/tools/xhs_note_reader.py `
  --url 'https://www.xiaohongshu.com/explore/<noteId>' `
  --state-file '.cache/xhs-state.json' `
  --out-json '.cache/xhs-extracted/note.json'
```

`--state-file` accepts either the runtime-state object itself, a wrapper containing `state` or `__INITIAL_STATE__`, or the sanitized snapshot emitted by the Chrome adapter. It does not fetch the URL or launch a browser. URL-based ID matching is preferred; a unique detail-map key can identify a note without an embedded note ID. Ambiguous state fails closed.

## Existing Chrome through chrome-use

If static HTML has no note data and the caller explicitly permits the real-browser adapter, use:

```powershell
python scripts/tools/xhs_note_reader.py `
  --url 'https://www.xiaohongshu.com/explore/<noteId>' `
  --browser-adapter chrome-use `
  --browser-login-state anonymous `
  --download-images `
  --out-json '.cache/xhs-extracted/note.json'
```

The `chrome-use` CLI and its connection to the intended Agent Chrome Profile must already be installed and working. The adapter checks `chrome-use status` and stops immediately if the extension relay is disconnected, so it does not wait on tab discovery or start/select another browser profile. With a live relay it lists tabs, adopts a matching open Xiaohongshu tab when available, and otherwise opens the URL in that connected Chrome. It takes a page snapshot, waits for normal page rendering, then evaluates a read-only extractor. It only builds a sanitized note snapshot from bounded state traversal and rendered DOM. The snapshot is written under `.cache/xhs-extracted/`; cookies, `localStorage`, tokens, and raw reactive state are not saved.

This is an explicit fallback: a successful static parse never reaches `chrome-use`. `300011`, CAPTCHA/security challenges, and rate-limit pages are hard stops; the reader does not retry or dismiss those controls. A normal login shell may use the explicitly selected existing Chrome profile, but the reader does not click through a login wall.

`--browser-login-state` records the caller's known session state (`authenticated`, `anonymous`, or `unknown`) without inspecting cookies or storage. Use `anonymous` for an Incognito session.

## Sequential batch in one pinned tab

When a batch must reuse a specific existing XHS tab, use the batch reader instead of repeatedly invoking the single-note command:

```powershell
python scripts/tools/xhs_note_batch_reader.py `
  --input-file 'C:\path\to\user-provided-links.txt' `
  --out-jsonl '.cache/xhs-extracted/batch.jsonl' `
  --checkpoint '.cache/xhs-extracted/batch.checkpoint.json' `
  --start-index 0 `
  --tab-id t2 `
  --session default `
  --chrome-use-path 'D:\Tools\chrome-use\chrome-use.exe'
```

At startup it checks that chrome-use's relay is live, the supplied tab is already adopted and on an XHS note, and a read-only page probe returns that same tab. Each source share URL is used only for navigation; the batch selects the pinned tab before each navigation, then verifies the resulting origin, `/explore/<noteId>` route, and note ID before extraction. The normal workflow never opens a replacement browser or profile.

After each successful note, the reader appends one normalized JSON object to JSONL and atomically advances `next_index` in the checkpoint. Existing successful note IDs in the JSONL are skipped. The checkpoint stores IDs and progress only, never source share URLs or `xsec_token`. A full `/login` route, CAPTCHA, `300011`/`300031`, rate limit, relay loss, route mismatch, or note-ID mismatch writes a sanitized stop record and checkpoint, then stops for human intervention. It does not continue to the next link.

For an explicitly requested debugging comparison, the batch can reuse an already running isolated `chrome-use --launch` session. Start that session on an XHS note in a clean, empty browser profile, then pass `--launch-context` and the same `--session` to the batch reader:

```powershell
chrome-use --launch --session xhs-debug-round-2 open '<first XHS note URL>'

python scripts/tools/xhs_note_batch_reader.py `
  --input-file 'C:\path\to\user-provided-links.txt' `
  --out-jsonl '.cache/xhs-extracted/batch.jsonl' `
  --checkpoint '.cache/xhs-extracted/batch.checkpoint.json' `
  --tab-id t1 `
  --session xhs-debug-round-2 `
  --launch-context `
  --chrome-use-path 'D:\Tools\chrome-use\chrome-use.exe'
```

This opt-in mode records `used_user_profile: false` and the isolated chrome-use session in provenance. It does not change the batch's stop-on-login/security/rate-limit behavior.

## Author profile

The profile reader uses the same existing-Chrome adapter; it does not open a fresh browser:

```powershell
python scripts/tools/xhs_profile_reader.py `
  --url 'https://www.xiaohongshu.com/user/profile/<userId>' `
  --out-json '.cache/xhs-extracted/profile.json'
```

It adopts a matching profile tab or opens the URL in the connected Chrome, reads the rendered profile fields/cards, and performs at most 10 ordinary page scrolls (`--scroll-steps`, default 4). A card cover is not the post's full gallery. If cards omit note IDs, the reader reports that limitation instead of guessing IDs or calling hidden endpoints.

## Provenance and output

The JSON `retrieval` object uses these modes:

- `static_html`: ordinary public HTML fetched without browser state.
- `saved_html`: local HTML parsed offline.
- `saved_runtime_state`: local JSON state or sanitized snapshot parsed offline.
- `real_chrome`: current Chrome profile read through `chrome-use`.

Real Chrome results set `used_user_profile: true` and `browser_automation: "chrome-use"`. `logged_in` follows the explicit `--browser-login-state` value and is never inferred by reading authentication material. Share URL query values such as `xsec_token` are redacted in JSON and cached snapshots.

The note result includes title, description, author, tags, engagement counts, timestamp, location, image variants, comments already rendered in the supplied snapshot, gallery counts, warnings, and errors. Image paths are present only when `--download-images` is used. Summarize image content with the agent's multimodal vision; this workflow runs no OCR model.

The comment compatibility wrapper is `scripts/tools/xhs_comment_reader.py`. The legacy `scripts/tools/profile_capture.py` entry point delegates to the current profile reader.
