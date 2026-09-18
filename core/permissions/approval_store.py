"""审批单持久化存储（data/approvals.jsonl）。"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from core.config import BASE_DIR

DATA_DIR = Path(BASE_DIR) / "data"
APPROVALS_FILE = DATA_DIR / "approvals.jsonl"

_lock = threading.RLock()
_seq = [0]


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _next_id() -> str:
    with _lock:
        _seq[0] += 1
        return f"apr_{int(time.time())}_{_seq[0]}"


def create_ticket(tool_call: Dict, risk: str, reason: str) -> Dict:
    _ensure()
    with _lock:
        ticket = {
            "ticket_id": _next_id(),
            "type": "tool_call",
            "tool": tool_call.get("tool"),
            "params": tool_call.get("params"),
            "reasoning": tool_call.get("reasoning", ""),
            "risk": risk,
            "reason": reason,
            "status": "pending",
            "created_at": time.time(),
            "resolved_at": None,
            "approved": None,
        }
        with open(APPROVALS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
        return ticket


def _load_all() -> List[Dict]:
    if not APPROVALS_FILE.exists():
        return []
    out = []
    try:
        with open(APPROVALS_FILE, "r", encoding="utf-8") as f:
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
    return out


def pending_tickets() -> List[Dict]:
    return [t for t in _load_all() if t.get("status") == "pending"]


def get_ticket(ticket_id: str) -> Optional[Dict]:
    for t in _load_all():
        if t.get("ticket_id") == ticket_id:
            return t
    return None


def resolve_ticket(ticket_id: str, approved: bool) -> Optional[Dict]:
    """把审批单标记为已处理，并重写文件（追加模式无法原地改，这里重写全文件）。"""
    _ensure()
    with _lock:
        all_tickets = _load_all()
        found = None
        for t in all_tickets:
            if t.get("ticket_id") == ticket_id and t.get("status") == "pending":
                t["status"] = "approved" if approved else "rejected"
                t["approved"] = approved
                t["resolved_at"] = time.time()
                found = t
                break
        if found is None:
            return None
        with open(APPROVALS_FILE, "w", encoding="utf-8") as f:
            for t in all_tickets:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        return found


def list_history(limit: int = 50) -> List[Dict]:
    all_tickets = _load_all()
    return all_tickets[-limit:][::-1]