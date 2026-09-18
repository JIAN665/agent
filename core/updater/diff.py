"""真实 diff：用 git 生成，不由模型自述。"""
from __future__ import annotations

import subprocess
from typing import List

from core.config import BASE_DIR


def _git(*args):
    r = subprocess.run(["git", "-C", str(BASE_DIR), *args],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    return r.returncode, r.stdout, r.stderr


def changed_files() -> List[str]:
    # 用 git status --porcelain 获取真实的改动/未跟踪文件（自动排除 .gitignore 忽略项）
    code, out, err = _git("status", "--porcelain")
    if code != 0:
        return []
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        path = line[3:].strip()
        if path:
            files.append(path)
    return files


def working_tree_diff() -> str:
    files = changed_files()
    if not files:
        return ""
    # 对未跟踪文件用 --no-index 对比 /dev/null 生成 diff；对已跟踪文件用 git diff
    parts = []
    code, out, err = _git("diff", "HEAD", "--", *files)
    if code == 0 and out:
        parts.append(out)
    # 未跟踪的新文件（不在 HEAD 里）单独处理
    for f in files:
        if _git("cat-file", "-e", f"HEAD:{f}")[0] != 0:
            code, content, err = _git("show", f":{f}")  # 拿暂存区内容（-N 后有了）
            # 简单方式：直接读文件内容构造一个简化 diff 头
            try:
                text = open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                text = ""
            parts.append(f"--- /dev/null\n+++ b/{f}\n@@ -0,0 +1,{len(text.splitlines())} @@\n"
                         + "\n".join("+" + ln for ln in text.splitlines()))
    return "\n".join(parts)

def summarize_diff(diff_text: str, files: List[str]) -> dict:
    added = sum(1 for l in diff_text.splitlines()
                if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_text.splitlines()
                  if l.startswith("-") and not l.startswith("---"))
    return {
        "file_count": len(files),
        "files": files,
        "lines_added": added,
        "lines_removed": removed,
        "short_summary": f"改动 {len(files)} 个文件，+{added} / -{removed} 行",
    }