"""权限策略：加载 sensitive_patterns.json，评估一次调用的风险等级。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.config import BASE_DIR

RULES_PATH = Path(BASE_DIR) / "config" / "sensitive_patterns.json"

DEFAULT_RULES: Dict = {
    "categories": [],
    "hard_block": [],
    "sensitive_paths": [],
    "risk_levels": {"low": "allow", "medium": "allow", "high": "approval", "critical": "approval"},
}

# 全局缓存（启动时加载一次）
_RULES: Dict = dict(DEFAULT_RULES)


class RiskDecision:
    """一次权限判定的结果。"""
    __slots__ = ("action", "risk", "reason", "matched_rule")

    def __init__(self, action: str, risk: str, reason: str, matched_rule: Optional[str] = None):
        self.action = action      # "allow" | "approval" | "deny"
        self.risk = risk          # "low" | "medium" | "high" | "critical"
        self.reason = reason
        self.matched_rule = matched_rule

    def to_dict(self) -> Dict:
        return {"action": self.action, "risk": self.risk,
                "reason": self.reason, "matched_rule": self.matched_rule}


def _load_defaults() -> None:
    global _RULES
    try:
        if RULES_PATH.exists():
            data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _RULES = {**DEFAULT_RULES, **data}
                return
    except Exception:
        pass
    _RULES = dict(DEFAULT_RULES)


def load_rules() -> Dict:
    """（重新）加载规则文件。"""
    _load_defaults()
    return _RULES


def get_rules() -> Dict:
    return _RULES


def _match_pattern(text: str, pattern: str) -> bool:
    p = pattern.strip()
    if not p:
        return False
    try:
        return re.search(p, text, re.IGNORECASE) is not None
    except re.error:
        return p.lower() in text.lower()


def evaluate(tool_name: str, params: Dict, tool_risk: str = "low") -> RiskDecision:
    """评估一次工具调用。返回 RiskDecision。
    优先级: 硬黑名单 deny > 敏感规则 approval > 工具默认风险。
    """
    text = json.dumps(params, ensure_ascii=False).lower()
    path_text = " ".join(str(v) for k, v in (params or {}).items()
                         if "path" in k or "dir" in k or "file" in k).lower()

    # 1. 硬黑名单 → 直接拒绝
    for hb in _RULES.get("hard_block", []):
        if hb and hb.lower() in text:
            return RiskDecision("deny", "critical",
                                f"命中硬黑名单: {hb.strip()}", matched_rule=hb.strip())

    # 2. 敏感路径
    for sp in _RULES.get("sensitive_paths", []):
        if sp and sp.lower() in path_text:
            return RiskDecision("approval", "critical",
                                f"涉及敏感路径: {sp}", matched_rule=sp)

    # 3. 敏感关键词
    for cat in _RULES.get("categories", []):
        patterns = cat.get("patterns", [])
        for pat in patterns:
            if pat and _match_pattern(text, pat):
                risk = cat.get("risk", "high")
                return RiskDecision("approval", risk,
                                    f"命中敏感词[{cat.get('name')}]: {pat}",
                                    matched_rule=cat.get("name"))

    # 4. 工具默认风险
    action = _RULES.get("risk_levels", {}).get(tool_risk, "approval")
    return RiskDecision(action, tool_risk, f"工具默认风险: {tool_risk}")


def get_risk_level(tool_risk: str) -> str:
    return tool_risk if tool_risk in ("low", "medium", "high", "critical") else "medium"


_load_defaults()