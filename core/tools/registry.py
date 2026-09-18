"""工具注册表。"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Dict, List, Optional

from core.tools.base import Tool

REGISTRY: Dict[str, Tool] = {}


def register(tool_obj: Tool) -> None:
    if not isinstance(tool_obj, Tool):
        raise TypeError("register() 需要 Tool 实例")
    REGISTRY[tool_obj.name] = tool_obj


def get_tool(name: str) -> Optional[Tool]:
    return REGISTRY.get(name)


def list_tools() -> List[Tool]:
    return sorted(REGISTRY.values(), key=lambda t: t.name)


def discover(package_name: str = "core.tools") -> None:
    """自动导入 core/tools 下所有模块，触发 @tool 装饰器注册。"""
    pkg = importlib.import_module(package_name)
    for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
        if modname.startswith("_"):
            continue
        importlib.import_module(f"{package_name}.{modname}")