"""自我更新工具：让模型能提出更新请求（不直接应用，需审批）。"""
from __future__ import annotations

from core.tools.base import tool
from core.updater.propose import propose_update


@tool(
    name="update.propose",
    description="提出一个自我更新请求（新增技能/修改代码/优化行为）。只创建提案，不会直接应用；应用前需要用户审批。",
    params_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "更新的简短概要（一句话）"},
            "description": {"type": "string", "description": "更新内容详细说明"},
            "update_type": {"type": "string",
                            "enum": ["code_update", "skill_add", "knowledge_add", "behavior_change"],
                            "description": "更新类型"},
        },
        "required": ["title", "description"],
    },
    risk_level="medium",
    category="system",
)
def update_propose(title: str, description: str, update_type: str = "code_update") -> str:
    p = propose_update(title, description, update_type=update_type)
    return f"已创建更新提案 {p['id']}：{p['title']}（待你审批）。请在更新管理控制台查看并批准。"