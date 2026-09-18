import json
import os
import shutil
import urllib.error
import urllib.request

import core.config as config
from core.tools.context import build_tools_context, build_tool_call_instruction


def resolve_ollama_model_dir():
    if os.path.exists(config.OLLAMA_HOME):
        return config.OLLAMA_HOME
    if os.path.exists(config.BUNDLED_MODELS_DIR):
        return config.BUNDLED_MODELS_DIR
    if config.USE_BUNDLED_OLLAMA and os.path.exists(config.BUNDLED_OLLAMA_HOME):
        return config.BUNDLED_OLLAMA_HOME
    return config.OLLAMA_HOME


def sync_bundled_ollama_files():
    if not config.USE_BUNDLED_OLLAMA or not config.AUTO_COPY_BUNDLED:
        return
    if not os.path.exists(config.BUNDLED_OLLAMA_HOME):
        return
    if os.path.exists(config.OLLAMA_HOME):
        return
    try:
        os.makedirs(os.path.dirname(config.OLLAMA_HOME), exist_ok=True)
        shutil.copytree(config.BUNDLED_OLLAMA_HOME, config.OLLAMA_HOME, dirs_exist_ok=True)
    except Exception:
        pass


def _normalize_model_name(name):
    if not name:
        return name
    cleaned = str(name).strip()
    if cleaned.endswith(":latest"):
        return cleaned
    return cleaned if cleaned.startswith("\"") else cleaned


def _extract_manifest_model_names(root_dir):
    names = set()
    manifests_root = os.path.join(root_dir, "models", "manifests")
    if not os.path.exists(manifests_root):
        return names
    for dirpath, dirnames, _ in os.walk(manifests_root):
        if not dirnames and os.path.basename(dirpath) == "latest":
            continue
        rel = os.path.relpath(dirpath, manifests_root)
        if rel == ".":
            continue
        parts = [p for p in rel.split(os.sep) if p and p != "."]
        if not parts:
            continue
        if len(parts) == 1 and parts[0].endswith("ollama.ai"):
            continue
        if len(parts) >= 2 and parts[-2] == "library":
            names.add(parts[-1])
        elif "library" in parts:
            library_idx = parts.index("library")
            if library_idx + 1 < len(parts):
                names.add(parts[library_idx + 1])
        elif len(parts) == 1:
            if not parts[0].endswith("ollama.ai"):
                names.add(parts[0])
    return {name for name in names if name and name != "latest"}


def list_available_ollama_models():
    candidates = []
    for root_dir in [config.OLLAMA_HOME, config.BUNDLED_OLLAMA_HOME, config.BUNDLED_MODELS_DIR]:
        if not os.path.exists(root_dir):
            continue
        for candidate in _extract_manifest_model_names(root_dir):
            candidates.append(candidate)
        for dirpath, _, filenames in os.walk(root_dir):
            manifests_dir = os.path.join(dirpath, "manifests")
            if os.path.exists(manifests_dir):
                for item in os.listdir(manifests_dir):
                    if item.endswith("ollama.ai"):
                        continue
                    candidates.append(item)
            for filename in filenames:
                if filename.endswith(".bin") or filename.endswith(".gguf"):
                    candidates.append(filename)
    seen = set()
    result = []
    for item in candidates:
        item = _normalize_model_name(item)
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def ensure_ollama_model_available():
    model_names = list_available_ollama_models()
    if not model_names:
        return

    user_home = os.path.expanduser("~")
    user_ollama_home = os.path.join(user_home, ".ollama")
    user_model_names = _extract_manifest_model_names(user_ollama_home)
    project_candidates = [
        config.OLLAMA_HOME,
        config.BUNDLED_OLLAMA_HOME,
        config.BUNDLED_MODELS_DIR,
    ]

    if not user_model_names:
        for candidate_dir in project_candidates:
            if os.path.exists(candidate_dir):
                try:
                    os.makedirs(os.path.dirname(user_ollama_home), exist_ok=True)
                    if os.path.basename(candidate_dir) == "models":
                        target = os.path.join(user_ollama_home, "models")
                        shutil.copytree(candidate_dir, target, dirs_exist_ok=True)
                    else:
                        shutil.copytree(candidate_dir, user_ollama_home, dirs_exist_ok=True)
                    break
                except Exception:
                    pass

    if config.MODEL not in model_names:
        config.MODEL = model_names[0]


def detect_local_ai_environment():
    messages = []
    ollama_path = shutil.which("ollama")
    if ollama_path:
        messages.append(f"Ollama 可执行文件已找到：{ollama_path}")
    else:
        messages.append("未找到 Ollama 可执行文件（请确认已安装并加入 PATH）")

    ollama_home_exists = os.path.exists(config.OLLAMA_HOME)
    if ollama_home_exists:
        messages.append(f"本地 Ollama 目录已存在：{config.OLLAMA_HOME}")
        try:
            items = os.listdir(config.OLLAMA_HOME)
            if items:
                messages.append(f"目录内容（前10项）：{', '.join(items[:10])}")
            else:
                messages.append(".ollama 目录为空")
        except Exception as exc:
            messages.append(f"无法读取 .ollama 目录：{exc}")
    else:
        messages.append(f"未找到本地 Ollama 目录：{config.OLLAMA_HOME}")

    builtin = None
    if os.path.exists(config.BUNDLED_MODELS_DIR):
        builtin = config.BUNDLED_MODELS_DIR
    elif os.path.exists(config.BUNDLED_OLLAMA_HOME):
        builtin = config.BUNDLED_OLLAMA_HOME

    if builtin:
        messages.append(f"检测到程序内置模型资源：{builtin}")
    else:
        messages.append(f"未检测到程序内置模型资源（路径：{config.BUNDLED_MODELS_DIR} 或 {config.BUNDLED_OLLAMA_HOME}）")

    models = list_available_ollama_models()
    if models:
        messages.append(f"检测到模型：{', '.join(models[:10])}")
    else:
        messages.append("未检测到可用模型文件")

    return "\n".join(messages)


def chat(model_messages):
    sync_bundled_ollama_files()
    ensure_ollama_model_available()
    from core.tools.context import build_tools_context, build_tool_call_instruction

def chat(model_messages):
    sync_bundled_ollama_files()
    ensure_ollama_model_available()
    # —— 新增：把工具清单注入第一条 system 消息（不修改已保存的历史）——
    prepared = []
    injected = False
    for m in model_messages:
        if not injected and m.get("role") == "system":
            content = m.get("content", "")
            if "可用工具清单" not in content:
                content = content + "\n\n" + build_tools_context() + "\n" + build_tool_call_instruction()
            prepared.append({"role": "system", "content": content})
            injected = True
        else:
            prepared.append(m)
    # —— 新增结束 ——
    model_candidates = []
    for name in [config.MODEL] + list_available_ollama_models():
        if name and name not in model_candidates:
            model_candidates.append(name)

    last_error = None
    for model_name in model_candidates:
        body = json.dumps({"model": model_name, "messages": prepared, "stream": False}).encode("utf-8")
        # ... 其余不变
    model_candidates = []
    for name in [config.MODEL] + list_available_ollama_models():
        if name and name not in model_candidates:
            model_candidates.append(name)

    last_error = None
    for model_name in model_candidates:
        body = json.dumps({"model": model_name, "messages": prepared, "stream": False}).encode("utf-8")
        request = urllib.request.Request(config.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"])
            config.MODEL = model_name
            return data["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode("utf-8")).get("error", str(exc))
            except Exception:
                err = str(exc)
            last_error = err
            if "not found" not in str(err).lower():
                raise RuntimeError(f"Ollama 返回错误：{err}")
            continue
        except Exception as exc:
            last_error = str(exc)
            if "not found" not in str(exc).lower():
                raise RuntimeError(f"Ollama 返回错误：{exc}")
            continue

    if last_error:
        raise RuntimeError(f"Ollama 返回错误：{last_error}")
    raise RuntimeError("未找到可用的 Ollama 模型，请确认模型已安装或执行 ollama pull <model-name>")
