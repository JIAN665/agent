"""工具上下文：生成给模型的提示词片段。"""
from __future__ import annotations

from core.tools.registry import list_tools

_RISK_LABEL = {"low": "低", "medium": "中", "high": "高", "critical": "危险"}


def build_tools_context() -> str:
    """返回工具清单文本（注入 SYSTEM_PROMPT / 对话）。"""
    tools = list_tools()
    if not tools:
        return "(当前没有可用工具)"
    lines = ["可用工具清单："]
    for t in tools:
        schema = t.params_schema or {}
        props = schema.get("properties", {})
        required = schema.get("required", [])
        param_desc = [f"{n}({p.get('type', '?')},{'必填' if n in required else '可选'})"
                      for n, p in props.items()]
        risk = _RISK_LABEL.get(t.risk_level, "?")
        lines.append(f"- {t.name}：{t.description} 参数: {', '.join(param_desc) or '无'} 风险: {risk}")
    return "\n".join(lines)


def build_tool_call_instruction() -> str:
    return (
        "当需要执行操作时，只输出一个 JSON 对象（不要 Markdown 代码块、不要其他文字）：\n"
        '{"tool": "<工具名>", "params": {<参数>}, "reasoning": "<简短说明为什么这么做>"}\n'
        "工具名和参数必须从上面的可用工具清单中选择。"
    )


def build_system_prompt(base_prompt: str) -> str:
    """把工具清单拼进系统提示词（替换掉现在 SYSTEM_PROMPT 里写死的 execute_command 描述）。"""
    return base_prompt + "\n\n" + build_tools_context() + "\n" + build_tool_call_instruction()