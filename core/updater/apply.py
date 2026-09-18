"""审批通过后：测试 → git 提交 + 打回滚点 → 记录历史。"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from core.config import BASE_DIR
from core.updater.diff import changed_files, summarize_diff, working_tree_diff
from core.updater.safety import check_safety
from core.updater.staging import run_tests
from core.updater.history import record_update


def _git(*args):
    r = subprocess.run(["git", "-C", str(BASE_DIR), *args],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    return r.returncode, r.stdout, r.stderr


def prepare_proposal(pid: str) -> dict:
    """审批前：生成真实 diff + 安全检查 + 统计，存回提案。"""
    from core.updater.propose import get_proposal, _save
    prop = get_proposal(pid)
    if prop is None:
        return {"ok": False, "message": f"提案不存在: {pid}"}

    files = changed_files()
    if not files:
        return {"ok": False, "message": "工作区没有未提交改动，无法生成更新（她还没改任何代码？）"}

    safety = check_safety(files)
    if not safety["safe"]:
        return {"ok": False, "message": safety["message"]}

    diff_text = working_tree_diff()
    stats = summarize_diff(diff_text, files)
    prop["status"] = "ready"
    prop["files"] = files
    prop["diff_stats"] = stats
    prop["diff"] = diff_text[:8000]
    _save(prop)
    return {"ok": True, "stats": stats, "diff": diff_text,
            "safety": safety, "proposal": prop}


def apply_proposal(pid: str, approved: bool = True) -> dict:
    """审批通过后应用；未通过则标记 rejected。"""
    from core.updater.propose import get_proposal, _save
    prop = get_proposal(pid)
    if prop is None:
        return {"ok": False, "message": f"提案不存在: {pid}"}

    if not approved:
        prop["status"] = "rejected"
        _save(prop)
        return {"ok": True, "applied": False, "message": "已拒绝，未应用"}

    # 1. 先跑测试（隔离验证）
    tests = run_tests()
    if not tests["passed"]:
        return {"ok": False, "applied": False,
                "message": "测试未通过，已阻止应用", "test_output": tests["output"]}

    # 2. 打回滚点（当前 HEAD）
    tag = f"pre-{pid}"
    _git("tag", tag)

    # 3. 提交
    code, out, err = _git("add", "-A")
    if code != 0:
        return {"ok": False, "applied": False, "message": f"git add 失败: {err}"}
    code, out, err = _git("commit", "-m", f"update: {pid}")
    if code != 0:
        return {"ok": False, "applied": False, "message": f"git commit 失败: {err}"}

    # 4. 更新状态 + 记录历史
    prop["status"] = "applied"
    prop["applied_at"] = time.time()
    prop["rollback_tag"] = tag
    _save(prop)
    record_update(pid, tag, title=prop.get("title", ""))
    return {"ok": True, "applied": True, "tag": tag,
            "message": f"已应用并提交，回滚点: {tag}"}


def rollback(pid: str) -> dict:
    """回滚到应用前的 tag。"""
    from core.updater.propose import get_proposal, _save
    prop = get_proposal(pid)
    if prop is None:
        return {"ok": False, "message": f"提案不存在: {pid}"}
    tag = prop.get("rollback_tag")
    if not tag:
        return {"ok": False, "message": "该提案没有回滚点（可能未应用）"}
    code, out, err = _git("reset", "--hard", tag)
    if code != 0:
        return {"ok": False, "message": f"回滚失败: {err}"}
    prop["status"] = "rolled_back"
    _save(prop)
    return {"ok": True, "message": f"已回滚到 {tag}"}