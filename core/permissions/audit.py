"""审计日志：只追加写入 data/audit.jsonl。"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from core.config import BASE_DIR

DATA_DIR = Path(BASE_DIR) / "data"
AUDIT_FILE = DATA_DIR / "audit.jsonl"

_lock = threading.RLock()


def get_audit_path() -> str:
    return str(AUDIT_FILE)


def log_event(event: str, detail: Optional[Dict] = None) -> None:
    """追加一条审计记录。只追加，不覆盖。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {"ts": time.time(), "event": event}
        if detail:
            # 控制单条大小，避免日志膨胀
            safe = {}
            for k, v in detail.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    safe[k] = v
                else:
                    safe[k] = str(v)[:1000]
            entry.update(safe)
        with _lock:
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_recent(limit: int = 50) -> list:
    if not AUDIT_FILE.exists():
        return []
    out = []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out[-limit:][::-1]