import json
import os
import threading
from pathlib import Path

from core.config import BASE_DIR

MEMORY_DB_PATH = Path(BASE_DIR) / "memory" / "memory_db.json"
LOCK = threading.RLock()

DEFAULT_DB = {"facts": [], "preferences": [], "corrections": []}


def _ensure_dir():
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_db():
    _ensure_dir()
    try:
        if MEMORY_DB_PATH.exists():
            return json.loads(MEMORY_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return json.loads(json.dumps(DEFAULT_DB))


DB = load_db()


def save_db():
    with LOCK:
        try:
            MEMORY_DB_PATH.write_text(json.dumps(DB, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


def add_memory(kind: str, content: str):
    """kind in ('facts','preferences','corrections')"""
    k = kind if kind in DB else None
    if not k:
        return False
    entry = {"content": content, "ts": __import__('time').time()}
    with LOCK:
        DB[k].append(entry)
    return True


def immediate_store_from_user_text(text: str):
    """Detect simple triggers in user text and store immediately.
    Patterns: '记住 ...', '不要 ...', '我喜欢 ...'"""
    t = text.strip()
    lowered = t.lower()
    if lowered.startswith("记住"):
        content = t[len("记住"):].strip()
        if content:
            add_memory("facts", content)
            save_db()
            return ("facts", content)
    if lowered.startswith("不要"):
        content = t[len("不要"):].strip()
        if content:
            add_memory("corrections", content)
            save_db()
            return ("corrections", content)
    if any(lowered.startswith(p) for p in ("我喜欢", "我喜歡", "i like")):
        # Support Chinese pref phrases
        if lowered.startswith("我喜欢") or lowered.startswith("我喜歡"):
            content = t[2:].strip()
        else:
            content = t
        add_memory("preferences", content)
        save_db()
        return ("preferences", content)
    return None


def retrieve_relevant_memories(query: str, max_results: int = 5):
    """Simple keyword-based retrieval: return items whose content overlaps query words."""
    if not query:
        return []
    q = query.lower()
    results = []
    with LOCK:
        for kind in ("facts", "preferences", "corrections"):
            for item in DB.get(kind, [])[::-1]:  # recent first
                content = item.get("content", "")
                if not content:
                    continue
                if any(w for w in q.split() if w and w in content.lower()):
                    results.append({"kind": kind, "content": content})
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
    return results


# Autosave thread helper
_AUTOSAVE_INTERVAL = 120
_autosave_thread = None
_autosave_stop = threading.Event()


def _autosave_loop():
    while not _autosave_stop.wait(_AUTOSAVE_INTERVAL):
        save_db()


def start_autosave():
    global _autosave_thread
    if _autosave_thread and _autosave_thread.is_alive():
        return
    _autosave_stop.clear()
    _autosave_thread = threading.Thread(target=_autosave_loop, daemon=True)
    _autosave_thread.start()


def stop_autosave():
    _autosave_stop.set()
    save_db()


# start autosave on import
start_autosave()
