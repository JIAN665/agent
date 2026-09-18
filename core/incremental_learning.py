import json
import os
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path
import shutil

from core.ollama_client import chat
from core.ollama_client import list_available_ollama_models, ensure_ollama_model_available
from core.config import BASE_DIR, ENABLE_REAL_FINETUNE
from memory.memory_db import add_memory, retrieve_relevant_memories, save_db, DB
from memory.chat_history import messages, save_chat_history


TRAINING_DIR = Path(BASE_DIR) / "training"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)

_validation_file = TRAINING_DIR / "validation_set.json"


def make_training_dataset_from_memory_and_history(max_examples=200):
    examples = []
    # create simple instruction-response pairs from recent messages
    recent = list(messages)[-200:]
    for i in range(0, len(recent) - 1):
        a = recent[i]
        b = recent[i + 1]
        if a.get("role") == "user" and b.get("role") == "assistant":
            examples.append({"prompt": a.get("content"), "response": b.get("content")})
        if len(examples) >= max_examples:
            break

    # supplement with memories as short facts
    for fact in DB.get("facts", [])[-50:]:
        examples.append({"prompt": "事实: %s\n请将其记住并在相关问题中考虑。" % fact.get("content"), "response": "已记住。"})
    return examples


def save_training_dataset(dataset, fname="dataset.jsonl"):
    p = TRAINING_DIR / fname
    with open(p, "w", encoding="utf-8") as f:
        for ex in dataset:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return str(p)


def _score_response(reference: str, candidate: str) -> float:
    if not reference or not candidate:
        return 0.0
    return SequenceMatcher(None, reference, candidate).ratio()


def evaluate_model_on_validation(model_name: str, validation_set=None):
    if validation_set is None:
        if _validation_file.exists():
            validation_set = json.loads(_validation_file.read_text(encoding="utf-8"))
        else:
            # build tiny validation from memory
            validation_set = [{"prompt": m.get("content"), "expected": m.get("content")} for m in DB.get("facts", [])[-10:]]

    total = 0.0
    count = 0
    for ex in validation_set:
        prompt = ex.get("prompt")
        expected = ex.get("expected") or ex.get("response") or ""
        try:
            resp = chat([{"role": "system", "content": "评价模式: 请简短回答"}, {"role":"user","content": prompt}])
        except Exception:
            continue
        score = _score_response(expected, resp)
        total += score
        count += 1
    return (total / count) if count else 0.0


def create_variant_model_tag(base_model: str, new_tag: str) -> bool:
    """Create a new model tag that points to the same manifest as base_model.
    This is a lightweight 'variant' so Ollama can load a model name like 'my-assistant-v2'.
    """
    # attempt to find base manifest under ~/.ollama or bundled
    user_home = os.path.expanduser("~")
    ollama_models_root = os.path.join(user_home, ".ollama", "models")
    # try to locate manifest JSON for base_model
    found = None
    for root in [ollama_models_root, os.path.join(BASE_DIR, "ollama_home", "models"), os.path.join(BASE_DIR, "models")]:
        for dirpath, dirnames, filenames in os.walk(root if os.path.exists(root) else []):
            # look for structure .../manifests/.../<base_model>/latest
            if base_model in dirpath and os.path.basename(dirpath) == base_model:
                # find 'latest' file siblings
                latest = os.path.join(dirpath, "latest")
                if os.path.exists(latest):
                    found = latest
                    break
        if found:
            break
    if not found:
        return False

    # create new manifest folder
    new_manifest_dir = os.path.join(ollama_models_root, "manifests", "local", new_tag)
    try:
        os.makedirs(new_manifest_dir, exist_ok=True)
        shutil.copyfile(found, os.path.join(new_manifest_dir, "latest"))
        return True
    except Exception:
        return False


def finetune_and_validate(base_model: str, new_model_tag: str, validation_set=None, timeout=600):
    """高层流程（注意：除非 ENABLE_REAL_FINETUNE=True，否则仅导出训练数据并返回说明）。

    - 生成训练数据集并保存（始终执行）
    - 如果 ENABLE_REAL_FINETUNE 为 True，调用实际的微调流程（尚未实现）并评估
    - 如果 ENABLE_REAL_FINETUNE 为 False，则明确返回未启用信息，避免任何"假评估"或伪造变体

    返回: (success: bool, details: dict)
    """
    dataset = make_training_dataset_from_memory_and_history()
    ds_path = save_training_dataset(dataset)

    # 如果未开启真实微调，安全退出并告知调用方：数据已导出，可用于离线训练
    if not ENABLE_REAL_FINETUNE:
        return (
            False,
            {
                "error": "REAL_FINETUNE_DISABLED",
                "message": (
                    "本地真实微调（ENABLE_REAL_FINETUNE）未启用。已生成训练数据集，但未执行任何微调或创建实际不同的模型。"
                    "这是为了避免产生误导性评估或伪造模型行为。要启用真实微调，请在 core.config 中将 ENABLE_REAL_FINETUNE 设为 True，"
                    "并确保本地有合适的训练工具链与计算资源。"
                ),
                "dataset_path": ds_path,
            },
        )

    # 以下为真实微调路径的占位（在启用时应由实际训练流程替代）
    # 目前不自动在进程内跑耗时训练；应调用外部训练脚本/工具并等待其完成/上报状态。
    # 为安全起见，这里仍然拒绝直接用 create_variant_model_tag() 作为微调替代。
    return False, {"error": "REAL_FINETUNE_ENABLED_BUT_NOT_IMPLEMENTED", "message": "已启用微调开关，但真实的本地微调流程尚未实现。请提供训练脚本或允许导出数据以在外部进行训练。", "dataset_path": ds_path}


# Background refiner
_refiner_thread = None
_refiner_stop = threading.Event()


def _refiner_loop(interval_seconds=300):
    while not _refiner_stop.wait(interval_seconds):
        try:
            # take last 50 messages and ask model to extract memories
            recent = list(messages)[-100:]
            texts = []
            for m in recent:
                texts.append(f"{m.get('role')}: {m.get('content')}")
            prompt = "请从下面对话中提炼事实、偏好和纠正，返回 JSON: {\"facts\":[],\"preferences\":[],\"corrections\":[]}\n\n" + "\n".join(texts)
            summary = None
            try:
                summary = chat([{"role": "system", "content": "记忆提炼助手"}, {"role": "user", "content": prompt}])
            except Exception:
                summary = None
            if summary:
                # try to parse JSON
                try:
                    j = json.loads(summary)
                    for f in j.get("facts", []):
                        add_memory("facts", f)
                    for p in j.get("preferences", []):
                        add_memory("preferences", p)
                    for c in j.get("corrections", []):
                        add_memory("corrections", c)
                except Exception:
                    # fallback: naive split by lines
                    for line in (summary or "").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("事实:") or line.startswith("Fact:"):
                            add_memory("facts", line)
                        elif line.startswith("我喜欢") or line.startswith("Preference:"):
                            add_memory("preferences", line)
                        elif line.startswith("纠正:") or line.startswith("Correction:"):
                            add_memory("corrections", line)
            # always persist memory
            save_db()
        except Exception:
            pass


def start_background_refiner(interval_seconds=300):
    global _refiner_thread
    if _refiner_thread and _refiner_thread.is_alive():
        return
    _refiner_stop.clear()
    _refiner_thread = threading.Thread(target=_refiner_loop, args=(interval_seconds,), daemon=True)
    _refiner_thread.start()


def stop_background_refiner():
    _refiner_stop.set()


# retrieve wrapper used by UI to get a text block
def retrieve_relevant_memories_text(query: str, max_results: int = 5):
    items = retrieve_relevant_memories(query, max_results=max_results)
    if not items:
        return ""
    lines = []
    for it in items:
        lines.append(f"[{it['kind']}] {it['content']}")
    return "\n".join(lines)
