"""工具分发器：校验 → 权限检查 → 执行/审批挂起 → 审计。

P2 阶段先提供可用的默认权限检查（按 risk_level + 敏感关键词）。
P4 会用 core/permissions 的正式闸门，通过 set_permission_checker 注入替换。
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from core.tools.base import Tool
from core.tools.registry import get_tool, list_tools


# ---------- 审批单（线程安全；P4 会换成持久化版本） ----------

class ApprovalStore:
    def __init__(self):
        self._tickets: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._seq = 0

    def create(self, tool_call: Dict, risk: str, reason: str) -> Dict:
        with self._lock:
            self._seq += 1
            ticket = {
                "ticket_id": f"apr_{int(time.time())}_{self._seq}",
                "type": "tool_call",
                "tool": tool_call.get("tool"),
                "params": tool_call.get("params"),
                "reasoning": tool_call.get("reasoning", ""),
                "risk": risk,
                "reason": reason,
                "status": "pending",
                "created_at": time.time(),
                "result": None,
            }
            self._tickets[ticket["ticket_id"]] = ticket
            return ticket

    def pending(self) -> List[Dict]:
        with self._lock:
            return [t for t in self._tickets.values() if t["status"] == "pending"]

    def resolve(self, ticket_id: str, approved: bool) -> Optional[Dict]:
        with self._lock:
            t = self._tickets.get(ticket_id)
            if not t or t["status"] != "pending":
                return None
            t["status"] = "approved" if approved else "rejected"
            return t


approval_store = ApprovalStore()

# ---------- 默认权限检查（P4 前的临时闸门） ----------

_SENSITIVE_KEYWORDS = [
    "银行卡", "卡号", "card number", "密码", "password", "passwd",
    "验证码", "otp", "2fa", "邮箱密码", "email password",
    "支付", "转账", "pay", "transfer", "通讯录", "联系人", "contact",
]
_SENSITIVE_PATTERNS = [r"\b\d{13,19}\b"]  # 长数字串（可能是卡号/账号）
_HARD_BLOCK_KEYWORDS = [
    "format ", "format:", "del /s", "rm -rf", "rd /s", "reg delete",
    "net user", "sc stop", "taskkill /f /im", "shutdown",
]

_RISK_TO_ACTION = {"low": "allow", "medium": "allow",
                   "high": "approval", "critical": "approval"}


def default_permission_checker(tool_obj: Tool, params: Dict) -> Dict:
    """默认闸门：返回 {"action": "allow"|"approval"|"deny", "reason": str}"""
    text = str(params).lower()
    for kw in _HARD_BLOCK_KEYWORDS:
        if kw in text:
            return {"action": "deny", "reason": f"命中硬黑名单关键词: {kw.strip()}"}
    for kw in _SENSITIVE_KEYWORDS:
        if kw in text:
            return {"action": "approval", "reason": f"涉及敏感信息关键词: {kw}"}
    for pat in _SENSITIVE_PATTERNS:
        if re.search(pat, text):
            return {"action": "approval", "reason": "涉及疑似卡号/账号等长数字串"}
    return {"action": _RISK_TO_ACTION.get(tool_obj.risk_level, "approval"),
            "reason": f"工具默认风险: {tool_obj.risk_level}"}


# ---------- 分发器 ----------
def _default_checker(tool_obj, params):
    """默认闸门：延迟导入 P4 正式闸门（避免循环导入）。"""
    from core.permissions.gate import check
    return check(tool_obj, params)
_permission_checker: Callable[[Tool, Dict], Dict] = _default_checker
_audit_hook: Optional[Callable[[Dict], None]] = None
_config_enabled = True


def set_permission_checker(checker: Callable[[Tool, Dict], Dict]) -> None:
    """注入权限检查器（P4 的 gate.check 会替换默认实现）。"""
    global _permission_checker
    _permission_checker = checker


def set_audit_hook(hook: Callable[[Dict], None]) -> None:
    """注入审计回调（P4 会接到 data/audit.jsonl）。"""
    global _audit_hook
    _audit_hook = hook


def set_enabled(enabled: bool) -> None:
    global _config_enabled
    _config_enabled = enabled


def _audit(entry: Dict) -> None:
    if _audit_hook:
        try:
            _audit_hook(entry)
        except Exception:
            pass


def dispatch(tool_call: Dict, require_approval: bool = True) -> Dict:
    """执行一次工具调用。

    入参（来自模型输出解析后）:
        {"tool": "shell.execute", "params": {...}, "reasoning": "..."}

    返回:
        {"status": "ok", "tool": ..., "result": ...}
        {"status": "needs_approval", "ticket": {...}}
        {"status": "denied", "tool": ..., "reason": ...}
        {"status": "error", "tool": ..., "error": ...}
        {"status": "unknown_tool", "tool": ..., "available": [...]}
    """
    if not _config_enabled:
        return {"status": "denied", "tool": tool_call.get("tool"),
                "reason": "工具总开关已关闭"}

    if not isinstance(tool_call, dict) or "tool" not in tool_call:
        return {"status": "error", "tool": None,
                "error": '工具调用格式无效，需要 {"tool": ..., "params": ...}'}

    name = str(tool_call.get("tool", "")).strip()
    params = tool_call.get("params") or {}
    reasoning = str(tool_call.get("reasoning", "") or "")

    tool_obj = get_tool(name)
    if tool_obj is None:
        return {"status": "unknown_tool", "tool": name,
                "available": [t.name for t in list_tools()]}

    # 1. 参数校验
    errors = tool_obj.validate(params)
    if errors:
        return {"status": "error", "tool": name,
                "error": "参数校验失败: " + "; ".join(errors)}

    # 2. 权限检查
    decision = _permission_checker(tool_obj, params)
    action = decision.get("action", "allow")
    reason = decision.get("reason", "")
    _audit({"event": "tool_check", "tool": name, "params": params,
            "action": action, "reason": reason, "ts": time.time()})

    if action == "deny":
        _audit({"event": "tool_denied", "tool": name, "params": params,
                "reason": reason, "ts": time.time()})
        return {"status": "denied", "tool": name, "reason": reason}

    if action == "approval":
        if require_approval:
            ticket = approval_store.create(tool_call,
                                           decision.get("risk") or tool_obj.risk_level,
                                           reason)
            _audit({"event": "tool_pending_approval", "ticket_id": ticket["ticket_id"],
                    "tool": name, "reason": reason, "ts": time.time()})
            return {"status": "needs_approval", "ticket": ticket}
        # require_approval=False：已由人工审批通过，放行

    # 3. 执行
    try:
        result = tool_obj.run(params)
        _audit({"event": "tool_ok", "tool": name, "params": params,
                "result": str(result)[:500], "ts": time.time()})
        return {"status": "ok", "tool": name, "result": result}
    except Exception as exc:
        _audit({"event": "tool_error", "tool": name, "params": params,
                "error": str(exc), "ts": time.time()})
        return {"status": "error", "tool": name,
                "error": f"{type(exc).__name__}: {exc}"}


def run_tool(tool_name: str, **params) -> Dict:
    """同步便捷入口：按名字+参数调用，直接过闸门（用于测试和 UI 直调）。"""
    return dispatch({"tool": tool_name, "params": params})


def resolve_approval(ticket_id: str, approved: bool) -> Dict:
    """审批结果回调：同意后重新执行挂起的工具调用（带 require_approval=False）。"""
    ticket = approval_store.resolve(ticket_id, approved)
    if ticket is None:
        return {"status": "error", "error": f"审批单不存在或已处理: {ticket_id}"}
    if not approved:
        _audit({"event": "tool_rejected", "ticket_id": ticket_id, "ts": time.time()})
        return {"status": "rejected", "ticket_id": ticket_id}
    _audit({"event": "tool_approved", "ticket_id": ticket_id, "ts": time.time()})
    return dispatch({"tool": ticket["tool"], "params": ticket["params"],
                     "reasoning": ticket.get("reasoning", "")},
                    require_approval=False)


def handle_model_reply(reply: str) -> Dict:
    """从模型回复文本中解析工具调用并分发（供 UI / 测试直接使用）。
    纯文本回复返回 {"status": "not_tool"}。兼容旧格式 execute_command / search_web / download_file。
    """
    from utils.text_utils import extract_json, looks_like_tool_reply
    if not looks_like_tool_reply(reply):
        return {"status": "not_tool"}
    try:
        parsed = extract_json(reply)
    except Exception as exc:
        return {"status": "error", "error": f"解析工具调用失败: {exc}"}
    if not isinstance(parsed, dict) or "tool" not in parsed:
        return {"status": "error", "error": "解析结果缺少 tool 字段"}

    # 旧格式兼容：{"tool": "execute_command", "command": "..."} → shell.execute
    if "params" not in parsed:
        params = {}
        old_map = {
            "execute_command": ("shell.execute", ["command"]),
            "search_web": ("web.search", ["query"]),
            "download_file": ("file.download", ["url", "filename", "save_dir"]),
            "download_image": ("file.download", ["url", "filename", "save_dir"]),
        }
        old_name = parsed.get("tool")
        if old_name in old_map:
            new_name, fields = old_map[old_name]
            parsed["tool"] = new_name
            for f in fields:
                if f in parsed:
                    params[f] = parsed[f]
        parsed["params"] = params
    return dispatch(parsed)