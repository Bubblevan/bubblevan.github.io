from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Sequence
from urllib.parse import urlsplit

from ..environment import environment_value


class ChromeUseError(RuntimeError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


class ChromeUseDriver:
    """Small shell-free adapter to the existing chrome-use CLI and an adopted tab."""

    def __init__(self, *, executable: str | None = None, timeout_seconds: float = 20.0,
                 runner=subprocess.run):
        configured = executable or environment_value("CHROME_USE_BIN")
        self.executable = configured or _find_executable()
        self.browser = (environment_value("CHROME_USE_BROWSER")
                        or environment_value("AGENT_BROWSER_PROFILE"))
        self.session = (environment_value("CHROME_USE_SESSION")
                        or environment_value("AGENT_BROWSER_SESSION"))
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))
        self.runner = runner
        self.tab_id = ""
        self.target_id = ""

    def _run(self, args: Sequence[str], *, input_text: str | None = None) -> Any:
        command = [self.executable, "--json"]
        if self.session:
            command.extend(["--session", self.session])
        command.extend(args)
        if self.browser and args and args[0] in {"open", "goto", "navigate"}:
            command.extend(["--browser", self.browser])
        # chrome-use may leave its session daemon alive after the CLI command exits.
        # PIPE capture then waits for EOF from the daemon's inherited handles. Use
        # short-lived files instead; these are closed and removed after each call.
        try:
            with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stdout_file, \
                    tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stderr_file:
                result = self.runner(
                    command, input=input_text, stdout=stdout_file, stderr=stderr_file,
                    text=True, encoding="utf-8", errors="replace",
                    timeout=self.timeout_seconds, check=False, shell=False,
                )
                stdout_file.flush()
                stdout_file.seek(0)
                output = stdout_file.read().strip()
        except FileNotFoundError as exc:
            raise ChromeUseError("relay_unavailable", "chrome-use executable is unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise ChromeUseError("relay_unavailable", "chrome-use command timed out") from exc
        if result.returncode:
            # Do not retain CLI output: it can contain rendered page text or URL query data.
            raise ChromeUseError("relay_unavailable", "chrome-use command failed")
        if not output:
            return {}
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"text": output}

    def status(self) -> dict[str, Any]:
        value = self._run(["status"])
        relay = _find_bool(value, {"relayUp", "relay_up", "extensionRelayUp"})
        return {"relay_up": relay is True}

    def tabs(self) -> list[dict[str, str]]:
        # --full provides stable targetId and ownership fields needed to safely
        # adopt one of the user's existing tabs. _clean_url strips query strings.
        value = self._run(["tab", "list", "--full"])
        rows = _find_tab_rows(value)
        clean = []
        for row in rows:
            url = _clean_url(str(row.get("url") or row.get("href") or ""))
            tab_id = str(row.get("tabId") or row.get("tab_id") or row.get("id") or "")[:120]
            target_id = str(row.get("targetId") or row.get("target_id") or "")[:120]
            ownership = str(row.get("ownership") or "")[:20]
            if tab_id and target_id:
                clean.append({"tab_id": tab_id, "target_id": target_id,
                              "url": url, "ownership": ownership})
        return clean

    def selected_tab_url(self) -> str:
        row = next((item for item in self.tabs() if item["tab_id"] == self.tab_id), None)
        return row["url"] if row and row["target_id"] == self.target_id else ""

    def adopt_tab(self, platform: str, *, requested_tab_id: str | None = None) -> dict[str, str]:
        if not self.status()["relay_up"]:
            raise ChromeUseError("relay_unavailable", "chrome-use extension relay is not connected")
        hosts = {"xiaohongshu": {"www.xiaohongshu.com", "xiaohongshu.com", "xhslink.com"},
                 "zhihu": {"www.zhihu.com", "zhihu.com", "zhuanlan.zhihu.com"}}
        allowed = hosts.get(platform)
        if not allowed:
            raise ValueError("unsupported social platform")
        tabs = self.tabs()
        selected = next((row for row in tabs if requested_tab_id and row["tab_id"] == requested_tab_id), None)
        if selected is None:
            selected = next((row for row in tabs if urlsplit(row["url"]).hostname in allowed), None)
        if selected is None or urlsplit(selected["url"]).hostname not in allowed:
            raise ChromeUseError("not_found", "no already-open tab matches the selected platform")
        if selected["ownership"] not in {"adopted", "created"}:
            self._run(["tab", "adopt", selected["target_id"]])
        self._run(["tab", "select", selected["tab_id"]])
        attached = next((row for row in self.tabs() if row["tab_id"] == selected["tab_id"]), None)
        if (not attached or attached["target_id"] != selected["target_id"] or
                attached["ownership"] not in {"adopted", "created"}):
            raise ChromeUseError("relay_unavailable", "adopted Chrome tab changed")
        self.tab_id, self.target_id = selected["tab_id"], selected["target_id"]
        return {key: attached[key] for key in ("tab_id", "target_id", "url", "ownership")}

    def navigate_selected_tab(self, url: str) -> None:
        if not self.tab_id or not self.target_id:
            raise ChromeUseError("not_found", "an existing tab must be adopted first")
        before = next((row for row in self.tabs() if row["tab_id"] == self.tab_id), None)
        if (not before or before["target_id"] != self.target_id or
                before["ownership"] not in {"adopted", "created"}):
            raise ChromeUseError("relay_unavailable", "adopted Chrome tab is no longer available")
        self._run(["tab", "select", self.tab_id])
        self._run(["open", url])
        after = next((row for row in self.tabs() if row["tab_id"] == self.tab_id), None)
        if not after or after["target_id"] != self.target_id:
            raise ChromeUseError("relay_unavailable", "navigation left the adopted Chrome tab")

    def snapshot(self) -> Any:
        if not self.tab_id or not self.target_id:
            raise ChromeUseError("not_found", "an existing tab must be adopted first")
        current = next((row for row in self.tabs() if row["tab_id"] == self.tab_id), None)
        if not current or current["target_id"] != self.target_id:
            raise ChromeUseError("relay_unavailable", "adopted Chrome tab is no longer available")
        return self._run(["snapshot"])

    def click_role(self, role: str, name: str) -> Any:
        """Click an accessible control by its role and exact visible name."""
        return self._run(["find", "role", role, "click", "--name", name])

    def click_selector(self, selector: str) -> Any:
        """Click a DOM selector; callers should keep selectors free of URL queries."""
        return self._run(["click", selector])

    def eval_json(self, script: str) -> Any:
        """Run a fixed platform extractor; returned fields remain in memory only."""
        if not self.tab_id or not self.target_id:
            raise ChromeUseError("not_found", "an existing tab must be adopted first")
        return _decode_payload(self._run(["eval", "--stdin"], input_text=script))


def _decode_payload(value: Any) -> Any:
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        elif isinstance(value, dict):
            for key in ("value", "result", "data", "output", "snapshot"):
                if key in value and isinstance(value[key], (str, dict, list)):
                    value = value[key]
                    break
            else:
                return value
        else:
            return value
    return value


def _find_bool(value: Any, names: set[str]) -> bool | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in names and isinstance(item, bool):
                return item
        for item in value.values():
            found = _find_bool(item, names)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_bool(item, names)
            if found is not None:
                return found
    return None


def _find_tab_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        rows = [item for item in value if isinstance(item, dict) and
                any(key in item for key in ("tabId", "tab_id", "targetId", "target_id"))]
        if rows:
            return rows
        for item in value:
            rows = _find_tab_rows(item)
            if rows:
                return rows
    elif isinstance(value, dict):
        for key in ("tabs", "items", "data", "result"):
            if key in value:
                rows = _find_tab_rows(value[key])
                if rows:
                    return rows
        for item in value.values():
            rows = _find_tab_rows(item)
            if rows:
                return rows
    return []


def _clean_url(value: str) -> str:
    from urllib.parse import urlsplit, urlunsplit
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        return urlunsplit((parsed.scheme, parsed.hostname.casefold(), parsed.path, "", ""))
    except ValueError:
        return ""


def _find_executable() -> str:
    for name in ("chrome-use", "chrome-use.exe"):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    fallback = _windows_default_path()
    if fallback is not None and fallback.is_file():
        return str(fallback)
    return "chrome-use"


def _windows_default_path() -> Path | None:
    # Codex may inherit a sandbox PATH that omits the user's installed tool directory.
    return Path(r"D:\DevTools\chrome-use\chrome-use.exe") if os.name == "nt" else None
