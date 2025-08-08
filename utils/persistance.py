# Simple JSON persistence helpers with basic file locking on *nix/Windows

from __future__ import annotations
from pathlib import Path
import json
import os
import time
from typing import Any, Callable

# Naive lock via .lock file (good enough for single-user local use)
def _lock_path(p: Path) -> Path:
    return p.with_suffix(p.suffix + ".lock")


def _acquire_lock(p: Path, timeout: float = 3.0, poll: float = 0.05) -> None:
    lock = _lock_path(p)
    start = time.time()
    while lock.exists():
        if time.time() - start > timeout:
            # Best-effort stale lock handling
            try:
                lock.unlink()
            except Exception:
                raise TimeoutError(f"Could not acquire lock for {p}")
        time.sleep(poll)
    lock.touch(exist_ok=True)


def _release_lock(p: Path) -> None:
    lock = _lock_path(p)
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass


def load_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        save_json(p, default)
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    _acquire_lock(p)
    try:
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    finally:
        _release_lock(p)


def update_json(path: str | Path, update_fn: Callable[[Any], Any], default: Any) -> Any:
    p = Path(path)
    cur = load_json(p, default)
    new = update_fn(cur)
    save_json(p, new)
    return new