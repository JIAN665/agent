import html
import json
import re


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未找到 JSON")
    return json.loads(t[start:end + 1])


def looks_like_tool_reply(text):
    if not isinstance(text, str):
        return False
    s = text.strip()
    if not s:
        return False
    lowered = s.lower()
    return (
        '"tool"' in lowered
        or 'execute_command' in lowered
        or 'search_web' in lowered
        or 'download_file' in lowered
        or 'download_image' in lowered
    )


def escape_html_text(text):
    return html.escape(str(text or "")).replace("\n", "<br>")
