"""正式权限闸门：替换 P2 的 default_permission_checker。"""
from __future__ import annotations

from typing import Dict

from core.permissions.policy import evaluate
from core.permissions.audit import log_event


def check(tool_obj, params: Dict) -> Dict:
    """P4 闸门入口。签名与 P2 的 set_permission_checker 兼容。
    tool_obj 是 core.tools.base.Tool 实例。
    """
    tool_risk = getattr(tool_obj, "risk_level", "low")
    decision = evaluate(tool_obj.name, params, tool_risk)

    log_event("tool_check", {
        "tool": tool_obj.name,
        "params": params,
        "action": decision.action,
        "risk": decision.risk,
        "reason": decision.reason,
        "matched_rule": decision.matched_rule,
    })

    return decision.to_dict()


def init_gate() -> None:
    """加载规则（幂等）。"""
    from core.permissions.policy import load_rules
    load_rules()


def install_gate() -> None:
    """把 P4 闸门注入 dispatcher，替换 P2 的默认检查器。"""
    from core.tools.dispatcher import set_permission_checker
    from core.tools import registry  # 确保工具已注册
    init_gate()
    set_permission_checker(check)