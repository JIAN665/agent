"""不可更新区校验：这些区域她永远不能改。"""
from __future__ import annotations

from typing import List

IMMUTABLE = [
    "core/permissions",          # 权限系统
    "core/updater",              # 更新管道自身
    "config/sensitive_patterns.json",  # 敏感规则
    "data",                      # 审计/审批/更新记录
]


def _norm(p: str) -> str:
    return str(p).replace("\\", "/").lower()


def check_safety(files: List[str]) -> dict:
    blocked = []
    for f in files:
        nf = _norm(f)
        for rule in IMMUTABLE:
            rn = _norm(rule)
            if nf == rn or nf.startswith(rn + "/"):
                blocked.append({"file": f, "rule": rule})
                break
    if blocked:
        return {"safe": False, "blocked": blocked,
                "message": f"更新涉及不可更新区，已拒绝: {blocked}"}
    return {"safe": True, "blocked": [], "message": "安全检查通过"}