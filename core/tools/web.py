"""联网/下载工具。"""
from __future__ import annotations

from core.command_executor import download_file, search_web
from core.tools.base import tool


@tool(
    name="web.search",
    description="打开浏览器搜索（需联网搜索开关开启）。",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["query"],
    },
    risk_level="low",
    category="web",
)
def web_search(query: str) -> str:
    return search_web(query)


@tool(
    name="file.download",
    description="下载网络文件到本地 downloads 目录。",
    params_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "文件 URL（http/https）"},
            "filename": {"type": "string", "description": "保存文件名（可选）"},
            "save_dir": {"type": "string", "description": "保存目录（可选，默认 downloads）"},
        },
        "required": ["url"],
    },
    risk_level="medium",
    category="web",
)
def file_download(url: str, filename: str = None, save_dir: str = None) -> str:
    return download_file(url=url, filename=filename, save_dir=save_dir)