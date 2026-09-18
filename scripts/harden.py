"""把不可更新区设为 Windows 只读（icacls）。
以管理员身份运行:  python scripts/harden.py
被锁的目录/文件，当前用户只有读+执行权限，程序（包括 shell 工具）无法修改。
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# 不可更新区（她不能改的）
IMMUTABLE = [
    BASE / "config" / "sensitive_patterns.json",
    BASE / "data" / "audit.jsonl",
    BASE / "data" / "approvals.jsonl",
]


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_icacls(path, args):
    cmd = ["icacls", str(path), *args]
    print(">", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def harden() -> None:
    if os.name != "nt":
        print("仅支持 Windows。")
        return
    if not is_admin():
        print("需要管理员权限。请右键以管理员身份运行。")
        sys.exit(1)
    user = os.environ.get("USERNAME", "")
    for p in IMMUTABLE:
        if not p.exists():
            print(f"跳过（不存在）: {p}")
            continue
        # 移除继承，只给当前用户读+执行，管理员完全控制
        run_icacls(p, ["/inheritance:r"])
        run_icacls(p, ["/grant:r", f"{user}:(RX)"])
        run_icacls(p, ["/grant:r", "Administrators:(F)"])
        print(f"已锁定: {p}")
    print("\n完成。注意：你自己改这些文件前要先运行 unharden.py。")


if __name__ == "__main__":
    harden()