"""解除只读锁（仅管理员）。用于你自己维护/修改被锁文件。"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

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


def unharden() -> None:
    if os.name != "nt":
        print("仅支持 Windows。")
        return
    if not is_admin():
        print("需要管理员权限。请右键以管理员身份运行。")
        sys.exit(1)
    for p in IMMUTABLE:
        if not p.exists():
            print(f"跳过（不存在）: {p}")
            continue
        subprocess.run(["icacls", str(p), "/reset"], capture_output=True, text=True)
        print(f"已解锁: {p}")
    print("\n完成。修改完记得重新运行 harden.py 锁回去。")


if __name__ == "__main__":
    unharden()