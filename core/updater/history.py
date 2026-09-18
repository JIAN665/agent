"""更新历史（data/updates.json）。"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core.config import BASE_DIR

HISTORY_FILE = Path(BASE_DIR) / "data" / "updates.json"
_lock = threading.RLock()


def _load() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def record_update(pid: str, tag: str, title: str = "", status: str = "applied") -> None:
    with _lock:
        hist = _load()
        hist.append({"pid": pid, "tag": tag, "title": title,
                     "status": status, "ts": time.time()})
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2),
                                encoding="utf-8")


def list_history() -> list:
    return _load()[::-1]