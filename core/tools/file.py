"""文件工具：读写、列目录、删除（删除风险高，会触发审批）。"""
from __future__ import annotations

import os

from utils.file_utils import normalize_path
from core.tools.base import tool

_MAX_READ_CHARS = 100_000


@tool(
    name="file.read",
    description="读取本地文本文件内容（最多前 100KB），用于解析本地文件并学习。",
    params_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件绝对路径"},
        },
        "required": ["path"],
    },
    risk_level="low",
    category="file",
)
def file_read(path: str) -> str:
    p = normalize_path(path)
    if not os.path.exists(p):
        return f"文件不存在: {p}"
    if os.path.isdir(p):
        return f"这是目录，不是文件: {p}"
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_READ_CHARS + 1)
        if len(content) > _MAX_READ_CHARS:
            content = content[:_MAX_READ_CHARS] + "\n...[内容过长已截断]..."
        return content
    except Exception as exc:
        return f"读取失败: {type(exc).__name__}: {exc}"


@tool(
    name="file.write",
    description="把文本写入本地文件（会覆盖已存在文件）。",
    params_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目标文件绝对路径"},
            "content": {"type": "string", "description": "要写入的文本内容"},
        },
        "required": ["path", "content"],
    },
    risk_level="medium",
    category="file",
)
def file_write(path: str, content: str) -> str:
    p = normalize_path(path)
    try:
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入: {p}（{len(content)} 字符）"
    except Exception as exc:
        return f"写入失败: {type(exc).__name__}: {exc}"


@tool(
    name="file.list",
    description="列出目录下的文件和子目录（不递归）。",
    params_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录绝对路径，默认项目根目录"},
        },
        "required": [],
    },
    risk_level="low",
    category="file",
)
def file_list(path: str = ".") -> str:
    p = normalize_path(path or ".")
    if not os.path.isdir(p):
        return f"目录不存在: {p}"
    try:
        items = sorted(os.listdir(p))
        lines = [f"{'[目录]' if os.path.isdir(os.path.join(p, i)) else '[文件]'} {i}" for i in items[:200]]
        if len(items) > 200:
            lines.append(f"...（共 {len(items)} 项，仅显示前 200）")
        return "\n".join(lines) if lines else "(空目录)"
    except Exception as exc:
        return f"列出失败: {type(exc).__name__}: {exc}"


@tool(
    name="file.delete",
    description="删除本地文件（不可恢复，风险高，必须审批）。",
    params_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要删除的文件绝对路径"},
        },
        "required": ["path"],
    },
    risk_level="critical",
    category="file",
)
def file_delete(path: str) -> str:
    p = normalize_path(path)
    if not os.path.exists(p):
        return f"文件不存在: {p}"
    if os.path.isdir(p):
        return "出于安全考虑，file.delete 仅支持删除文件，不支持删除目录。"
    try:
        os.remove(p)
        return f"已删除: {p}"
    except Exception as exc:
        return f"删除失败: {type(exc).__name__}: {exc}"