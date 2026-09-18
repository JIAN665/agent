"""Shell 工具：执行本地命令（P2 封装，替代裸 shell=True 直跑）。"""
from __future__ import annotations

from core.command_executor import run_command
from core.tools.base import tool


@tool(
    name="shell.execute",
    description="在本地电脑上执行一条 shell 命令并返回输出。仅用于用户明确要求的本地操作，敏感命令会被权限层拦截。",
    params_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令（如 dir、python -c ...）"},
            "timeout": {"type": "integer", "description": "超时秒数（保留字段，当前版本未强制执行）"},
        },
        "required": ["command"],
    },
    risk_level="medium",
    category="system",
)
def shell_execute(command: str, timeout: int = 30) -> str:
    return run_command(command)