"""P2 结构化工具层。导入本包即自动注册所有内置工具。"""

from core.tools.base import Tool, tool, validate_params
from core.tools.registry import get_tool, list_tools, register, discover
from core.tools.dispatcher import (
    ApprovalStore, approval_store, dispatch, run_tool, resolve_approval,
    handle_model_reply, set_permission_checker, set_audit_hook, set_enabled,
)
from core.tools.context import (
    build_tools_context, build_tool_call_instruction, build_system_prompt,
)

__all__ = [
    "Tool", "tool", "validate_params",
    "get_tool", "list_tools", "register", "discover",
    "ApprovalStore", "approval_store", "dispatch", "run_tool", "resolve_approval",
    "handle_model_reply", "set_permission_checker", "set_audit_hook", "set_enabled",
    "build_tools_context", "build_tool_call_instruction", "build_system_prompt",
]


def _auto_discover() -> None:
    """导入所有 core/tools/*.py，触发 @tool 装饰器注册。"""
    try:
        discover()
    except Exception:
        pass


_auto_discover()