"""Ollama 启动器：检测服务是否在运行；未运行则自动拉起（优先用项目内 ollama.exe 和模型目录）。"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import core.config as config

OLLAMA_VERSION_URL = config.OLLAMA_BASE + "/api/version"
STARTUP_TIMEOUT = 60  # 秒


def ollama_running() -> bool:
    """检测 Ollama 服务是否已在运行。"""
    try:
        with urllib.request.urlopen(OLLAMA_VERSION_URL, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _find_ollama_exe() -> str | None:
    """定位 ollama.exe：系统安装版优先，其次项目内，最后 PATH。"""
    candidates = []
    sys_exe = getattr(config, "SYSTEM_OLLAMA_EXE", None)   # 如果 config 里配了就用
    if sys_exe:
        candidates.append(sys_exe)
    candidates += [
        r"D:\Ollama\ollama.exe",                          # 你机器上的系统版
        str(Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"),
        r"C:\Program Files\Ollama\ollama.exe",
    ]
    for exe in candidates:
        if exe and os.path.exists(exe):
            return exe
    if os.path.exists(config.BUNDLED_OLLAMA_EXE):        # 项目内（残缺版，兜底）
        return config.BUNDLED_OLLAMA_EXE
    return shutil.which("ollama")

def _resolve_models_dir() -> str | None:
    """模型目录：指向真正含 manifests/ 的目录（bundled 优先，其次系统默认）。"""
    for d in (config.BUNDLED_OLLAMA_HOME, config.BUNDLED_MODELS_DIR):
        if not d:
            continue
        if os.path.exists(os.path.join(d, "models", "manifests")):
            return os.path.join(d, "models")      # 布局: <d>/models/manifests
        if os.path.exists(os.path.join(d, "manifests")):
            return d                              # 布局: <d>/manifests
    user_models = os.path.join(os.path.expanduser("~"), ".ollama", "models")
    try:
        if os.path.exists(user_models) and os.listdir(user_models):
            return None
    except Exception:
        pass
    return None


def start_ollama() -> dict:
    """启动 Ollama 服务（已运行则直接返回）。"""
    if ollama_running():
        return {"started": False, "message": "Ollama 已在运行"}
    exe = _find_ollama_exe()
    if not exe:
        return {"started": False, "message": "未找到 ollama.exe（项目内或 PATH 均无）"}

    env = dict(os.environ)
    models_dir = _resolve_models_dir()
    if models_dir:
        env["OLLAMA_MODELS"] = models_dir

    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen([exe, "serve"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=flags)
    except Exception as exc:
        return {"started": False, "message": f"启动 ollama 失败: {exc}"}

    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline:
        if ollama_running():
            return {"started": True, "message": f"Ollama 已启动（{exe}）", "pid": proc.pid}
        time.sleep(1)
    return {"started": False, "message": "Ollama 启动超时，请检查模型目录或手动运行 ollama serve"}


def ensure_ollama(timeout: int = 60) -> dict:
    """主入口：确保 Ollama 服务可用。"""
    global STARTUP_TIMEOUT
    STARTUP_TIMEOUT = timeout
    if ollama_running():
        return {"started": False, "message": "Ollama 已在运行"}
    return start_ollama()