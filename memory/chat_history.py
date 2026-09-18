import json

from core.config import BASE_DIR, SYSTEM_PROMPT

MEMORY_DIR = BASE_DIR / "chat_memory"
MEMORY_FILE = MEMORY_DIR / "chat_history.json"


def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def load_chat_history():
    ensure_memory_dir()
    if not MEMORY_FILE.exists():
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("history is not a list")
        cleaned = []
        for item in data:
            if isinstance(item, dict) and "role" in item and "content" in item:
                cleaned.append({"role": str(item["role"]), "content": str(item["content"])})
        if not cleaned or cleaned[0].get("role") != "system":
            cleaned.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        return cleaned
    except Exception:
        return [{"role": "system", "content": SYSTEM_PROMPT}]


def save_chat_history(messages):
    ensure_memory_dir()
    try:
        MEMORY_FILE.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_chat_history():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    save_chat_history(messages)
    return messages


messages = load_chat_history()
