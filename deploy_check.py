"""新电脑部署检查：一键检查 Python、依赖、Ollama、模型、Git、权限锁状态。
用法（新电脑上，项目根目录）:  python deploy_check.py
"""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
OK, WARN, FAIL = "✅", "⚠️", "❌"


def check_python():
    print(f"\n[1] Python")
    print(f"    当前解释器: {sys.executable}")
    print(f"    版本: {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print(f"    {FAIL} 版本过低，需 3.8+")
    else:
        print(f"    {OK} 版本满足要求")


def check_deps():
    print(f"\n[2] 依赖库")
    required = {
        "PySide6": "pyside6",
        "vosk": "vosk",
        "sounddevice": "sounddevice",
        "SpeechRecognition": "speech_recognition",
        "pyttsx3": "pyttsx3",
    }
    for name, module in required.items():
        try:
            importlib.import_module(module)
            print(f"    {OK} {name} 已安装")
        except Exception:
            print(f"    {WARN} {name} 未安装（语音功能需要，聊天不需要）")


def check_ollama():
    print(f"\n[3] Ollama 服务")
    # 项目内 exe
    bundled = BASE / "ollama.exe"
    sys_ollama = shutil.which("ollama")
    if bundled.exists():
        print(f"    {OK} 项目内 ollama.exe 存在: {bundled}")
    elif sys_ollama:
        print(f"    {OK} 系统 PATH 找到 ollama: {sys_ollama}")
    else:
        print(f"    {FAIL} 未找到 ollama.exe（项目内或 PATH 均无）")

    # 服务是否在运行
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/version", timeout=2) as r:
            print(f"    {OK} Ollama 服务正在运行: {r.read().decode()[:50]}")
    except Exception:
        print(f"    {WARN} Ollama 服务未运行（程序启动时会自动拉起，若失败请手动 ollama serve）")


def check_model():
    print(f"\n[4] 模型")
    manifests = BASE / "ollama_home" / "models" / "manifests"
    if manifests.exists():
        models = []
        for p in manifests.rglob("*"):
            if p.is_file() and p.name not in ("latest",):
                models.append(p.parent.name)
        if models:
            print(f"    {OK} 项目内模型: {', '.join(sorted(set(models)))}")
        else:
            print(f"    {WARN} 项目内模型目录存在但未识别到模型")
    else:
        print(f"    {FAIL} 项目内未找到模型（ollama_home/models/manifests 不存在）")
        print(f"         → 若新电脑系统已装 Ollama，请确认 ~/.ollama 有模型")


def check_git():
    print(f"\n[5] Git")
    git_exe = shutil.which("git")
    if git_exe:
        try:
            ver = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
            print(f"    {OK} Git 已安装: {ver}")
        except Exception:
            print(f"    {WARN} git 命令异常")
    else:
        print(f"    {FAIL} Git 未安装（回滚/自更新功能需要，聊天不需要）")

    if (BASE / ".git").exists():
        print(f"    {OK} .git 历史目录存在（项目历史已带过来）")
        code = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True,
                              cwd=str(BASE))
        if code.returncode == 0:
            print(f"    {OK} 最近提交:\n{code.stdout.strip()}")
        else:
            print(f"    {WARN} git log 失败（可能需要解锁或仓库状态问题）")
    else:
        print(f"    {FAIL} .git 不存在（项目历史没带过来，或未初始化）")


def check_memory():
    print(f"\n[6] 记忆数据")
    for p in (BASE / "chat_memory" / "chat_history.json",
              BASE / "memory" / "memory_db.json"):
        if p.exists():
            size = p.stat().st_size
            print(f"    {OK} {p.relative_to(BASE)} ({size} 字节)")
        else:
            print(f"    {WARN} {p.relative_to(BASE)} 不存在（新电脑无历史记忆）")


def check_locks():
    print(f"\n[7] 权限锁状态")
    locked = [
        BASE / "config" / "sensitive_patterns.json",
        BASE / "data" / "audit.jsonl",
    ]
    for p in locked:
        if not p.exists():
            print(f"    {WARN} {p.relative_to(BASE)} 不存在")
            continue
        # 尝试写测试（以追加方式打开会失败说明只读）
        try:
            with open(p, "a", encoding="utf-8") as f:
                pass
            print(f"    {WARN} {p.relative_to(BASE)} 可写（未上锁）")
        except PermissionError:
            print(f"    {OK} {p.relative_to(BASE)} 已锁定（只读）")


def main():
    print("=" * 58)
    print("澪玖 · 新电脑部署检查")
    print(f"项目目录: {BASE}")
    print("=" * 58)

    check_python()
    check_deps()
    check_ollama()
    check_model()
    check_git()
    check_memory()
    check_locks()

    print("\n" + "=" * 58)
    print("检查完成。❌ = 必须解决，⚠️ = 建议处理，✅ = 正常")
    print("之后启动: python main.py")
    print("=" * 58)


if __name__ == "__main__":
    main()