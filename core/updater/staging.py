"""隔离验证：应用前先跑全量测试。"""
from __future__ import annotations

import subprocess
import sys

from core.config import BASE_DIR


def run_tests() -> dict:
    cmd = [sys.executable, "-m", "unittest", "discover",
           "-s", "tests", "-p", "test_*.py"]
    r = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True,
                       text=True, encoding="utf-8", errors="ignore")
    tail = (r.stdout + r.stderr)[-2000:]
    return {"passed": r.returncode == 0, "returncode": r.returncode, "output": tail}