from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import portalocker


class LockContended(RuntimeError):
    """A writer lock could not be acquired within its bounded wait."""


def store_lock_path(runtime_dir: Path | str) -> Path:
    return Path(runtime_dir) / "locks" / "store-write.lock"


def feed_lock_path(private_dir: Path | str) -> Path:
    return Path(private_dir).parent / "locks" / "feed-write.lock"


@contextmanager
def writer_lock(path: Path | str, *, timeout_seconds: float, purpose: str) -> Iterator[None]:
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with portalocker.Lock(str(lock_path), mode="a", timeout=timeout_seconds,
                             check_interval=0.1,
                             flags=portalocker.LOCK_EX | portalocker.LOCK_NB):
            yield
    except portalocker.exceptions.LockException as exc:
        raise LockContended(f"lock_contended: {purpose}") from exc


@contextmanager
def store_writer_lock(runtime_dir: Path | str, *, timeout_seconds: float = 5.0) -> Iterator[None]:
    with writer_lock(store_lock_path(runtime_dir), timeout_seconds=timeout_seconds,
                     purpose="store write"):
        yield


@contextmanager
def feed_writer_lock(private_dir: Path | str, *, timeout_seconds: float = 5.0) -> Iterator[None]:
    with writer_lock(feed_lock_path(private_dir), timeout_seconds=timeout_seconds,
                     purpose="feed write"):
        yield
