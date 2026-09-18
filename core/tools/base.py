"""工具（Tool）基础定义。

P2 结构化工具层：把"模型直接执行命令"改成"统一工具调用"。
每个工具 = name + description + params_schema(JSON Schema) + risk_level + handler。
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


def _validate_value(value: Any, schema: Dict, path: str = "params") -> List[str]:
    """极简 JSON Schema 校验（不依赖 jsonschema 库）。返回错误列表。"""
    errors: List[str] = []
    t = schema.get("type")
    if t and value is not None:
        if t == "string" and not isinstance(value, str):
            errors.append(f"{path}: 期望 string，得到 {type(value).__name__}")
        elif t == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append(f"{path}: 期望 integer，得到 {type(value).__name__}")
        elif t == "number" and not isinstance(value, (int, float)):
            errors.append(f"{path}: 期望 number，得到 {type(value).__name__}")
        elif t == "boolean" and not isinstance(value, bool):
            errors.append(f"{path}: 期望 boolean，得到 {type(value).__name__}")
        elif t == "array" and not isinstance(value, list):
            errors.append(f"{path}: 期望 array，得到 {type(value).__name__}")
        elif t == "object" and not isinstance(value, dict):
            errors.append(f"{path}: 期望 object，得到 {type(value).__name__}")
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{path}: 值 {value!r} 不在允许范围内 {enum}")
    return errors


def validate_params(params: Any, schema: Optional[Dict]) -> List[str]:
    """校验工具参数。params 必须是 dict；缺必填、类型不符都返回错误。"""
    if not isinstance(params, dict):
        return ["params 必须是 JSON 对象"]
    if not schema:
        return []
    errors: List[str] = []
    props = schema.get("properties", {})
    required = schema.get("required", [])
    for name in required:
        if name not in params:
            errors.append(f"缺少必填参数: {name}")
    for name, value in params.items():
        if name in props:
            errors.extend(_validate_value(value, props[name], f"params.{name}"))
    return errors


@dataclass
class Tool:
    """一个可被模型调用的工具。"""
    name: str
    description: str
    handler: Callable
    params_schema: Optional[Dict] = None
    risk_level: str = "low"      # low / medium / high / critical
    category: str = "general"
    requires_approval: Optional[Callable[[Dict], bool]] = None

    def validate(self, params: Dict) -> List[str]:
        return validate_params(params, self.params_schema)

    def run(self, params: Dict) -> Any:
        """执行工具（只过滤签名里的参数，模型多传的字段忽略，避免 TypeError）。"""
        sig = inspect.signature(self.handler)
        accepted = set(sig.parameters) - {"self", "cls"}
        filtered = {k: v for k, v in params.items() if k in accepted}
        return self.handler(**filtered)


def _first_doc_line(fn: Callable) -> str:
    doc = (fn.__doc__ or "").strip()
    return doc.splitlines()[0] if doc else ""


def tool(name=None, description=None, params_schema=None, risk_level="low",
         category="general", requires_approval=None):
    """装饰器：把普通函数变成 Tool 并注册到全局注册表。

    用法:
        @tool(name="shell.execute", description="...", params_schema={...}, risk_level="medium")
        def shell_execute(command, timeout=30):
            ...
    """
    def decorator(fn):
        from core.tools.registry import register  # 延迟导入避免循环依赖
        t = Tool(
            name=name or fn.__name__,
            description=description or _first_doc_line(fn),
            handler=fn,
            params_schema=params_schema or _infer_schema(fn),
            risk_level=risk_level,
            category=category,
            requires_approval=requires_approval,
        )
        register(t)
        return fn
    return decorator


def _infer_schema(fn: Callable) -> Dict:
    """从函数签名推断最简 schema（仅在未显式提供 params_schema 时兜底）。"""
    sig = inspect.signature(fn)
    props: Dict[str, Dict] = {}
    required: List[str] = []
    type_map = {str: "string", int: "integer", float: "number",
                bool: "boolean", list: "array", dict: "object"}
    for pname, p in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        ptype = type_map.get(p.annotation, "string")
        entry = {"type": ptype}
        if p.default is not inspect.Parameter.empty:
            entry["default"] = p.default
        else:
            required.append(pname)
        props[pname] = entry
    return {"type": "object", "properties": props, "required": required}