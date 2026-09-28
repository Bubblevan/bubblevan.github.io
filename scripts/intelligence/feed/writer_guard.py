from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import tempfile


class ActiveFeedWriterError(RuntimeError):
    pass


def ensure_cli_writer_available(private_dir: Path | str) -> None:
    path = Path(private_dir) / ".ui-writer.json"
    if not path.exists():
        return
    try:
        owner = json.loads(path.read_text(encoding="utf-8"))
        pid = int(owner.get("pid", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raise ActiveFeedWriterError(f"feed writer marker is malformed; stop the UI and inspect {path}")
    if _pid_alive(pid):
        raise ActiveFeedWriterError(f"Streamlit feed UI is the active writer (pid {pid}); stop it before CLI mutation")
    try:
        path.unlink()
    except OSError as exc:
        raise ActiveFeedWriterError(f"stale feed writer marker cannot be cleared: {path}") from exc


def acquire_ui_writer(private_dir: Path | str) -> Path:
    directory = Path(private_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".ui-writer.json"
    payload = json.dumps({"pid": os.getpid(), "process": "streamlit-feed"}, sort_keys=True) + "\n"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            owner = json.loads(path.read_text(encoding="utf-8"))
            if int(owner.get("pid", 0)) == os.getpid() and owner.get("process") == "streamlit-feed":
                return path
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        ensure_cli_writer_available(directory)
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    def release() -> None:
        try:
            owner = json.loads(path.read_text(encoding="utf-8"))
            if int(owner.get("pid", 0)) == os.getpid():
                path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    atexit.register(release)
    return path


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True
