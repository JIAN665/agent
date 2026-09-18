"""更新提案的创建与查询（保存到 data/pending_updates/）。"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from core.config import BASE_DIR

PENDING_DIR = Path(BASE_DIR) / "data" / "pending_updates"
_lock = threading.RLock()
_seq = [0]


def _next_id() -> str:
    with _lock:
        _seq[0] += 1
        return f"upd_{int(time.time())}_{_seq[0]}"


def propose_update(title: str, description: str,
                   reason: str = "", update_type: str = "code_update") -> Dict:
    """创建一个更新提案（不应用，等审批）。"""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        pid = _next_id()
        proposal = {
            "id": pid,
            "type": update_type,
            "title": title,
            "description": description,
            "reason": reason,
            "status": "proposed",     # proposed → ready → applied / rejected / rolled_back
            "created_at": time.time(),
            "files": [],
            "diff_stats": None,
            "diff": None,
            "applied_at": None,
            "rollback_tag": None,
        }
        (PENDING_DIR / f"{pid}.json").write_text(
            json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        return proposal


def get_proposal(pid: str) -> Optional[Dict]:
    p = PENDING_DIR / f"{pid}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def list_proposals() -> List[Dict]:
    if not PENDING_DIR.exists():
        return []
    out = []
    for f in sorted(PENDING_DIR.glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def _save(proposal: Dict) -> None:
    (PENDING_DIR / f"{proposal['id']}.json").write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")