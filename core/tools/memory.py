"""记忆工具：把已有的 memory_db 接进工具层（之前一直没接线，这里接上）。"""
from __future__ import annotations

from memory.memory_db import add_memory, retrieve_relevant_memories, save_db
from core.tools.base import tool

_KINDS = ("facts", "preferences", "corrections")


@tool(
    name="memory.store",
    description="把一条长期记忆写入记忆库（facts=事实，preferences=偏好，corrections=纠正/禁止事项）。",
    params_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": list(_KINDS), "description": "记忆类型"},
            "content": {"type": "string", "description": "要记住的内容"},
        },
        "required": ["kind", "content"],
    },
    risk_level="low",
    category="memory",
)
def memory_store(kind: str, content: str) -> str:
    ok = add_memory(kind, content)
    if not ok:
        return f"记忆类型无效，可选: {', '.join(_KINDS)}"
    save_db()
    return f"已记住 [{kind}]: {content}"


@tool(
    name="memory.retrieve",
    description="按关键词检索长期记忆，返回相关条目（用于回忆用户之前说过的内容）。",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索关键词"},
            "max_results": {"type": "integer", "description": "最多返回条数"},
        },
        "required": ["query"],
    },
    risk_level="low",
    category="memory",
)
def memory_retrieve(query: str, max_results: int = 5) -> str:
    items = retrieve_relevant_memories(query, max_results=max_results)
    if not items:
        return "(没有相关记忆)"
    return "\n".join(f"[{it['kind']}] {it['content']}" for it in items)