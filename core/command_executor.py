import os
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

import core.config as config


def run_command(cmd):
    try:
        if sys.platform.startswith("win"):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout + (("\n[错误] " + result.stderr) if result.stderr else "")
        return output.strip() if output.strip() else "(无输出)"
    except Exception as exc:
        return f"执行失败: {exc}"


def search_web(query):
    if not config.ENABLE_WEB_SEARCH:
        return "联网搜索已关闭。若要启用，请勾选“联网搜索”开关。"
    if not query or not query.strip():
        return "搜索关键词为空。"

    safe_query = query.strip()
    bing_url = "https://www.bing.com/search?q=" + urllib.parse.quote(safe_query)

    try:
        with urllib.request.urlopen(bing_url, timeout=15) as resp:
            status = getattr(resp, "status", None)
            if status is not None and status >= 400:
                raise RuntimeError(f"HTTP status={status}")
    except Exception as net_err:
        return f"联网搜索失败：真实错误：{type(net_err).__name__}: {net_err} | 目标={bing_url}"

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge_exe = next((path for path in edge_paths if os.path.exists(path)), None)
    try:
        if edge_exe:
            subprocess.Popen([edge_exe, bing_url], shell=False)
            return f"已使用 Edge 打开搜索页：{bing_url}"
        webbrowser.open_new_tab(bing_url)
        return f"已打开默认浏览器搜索：{bing_url}"
    except Exception as exc:
        return f"联网搜索失败：真实错误：{type(exc).__name__}: {exc} | 目标={bing_url}"


def download_file(url, filename=None, save_dir=None):
    if not url or not str(url).startswith(("http://", "https://")):
        raise ValueError(f"非法下载地址：{url}")

    target_dir = os.path.abspath(save_dir or config.DOWNLOADS_DIR)
    os.makedirs(target_dir, exist_ok=True)

    if filename:
        target_name = filename.strip()
    else:
        parsed = urllib.parse.urlparse(url)
        target_name = os.path.basename(parsed.path) or "download_file"
        if not target_name or "." not in target_name:
            target_name = "download_file"

    full_path = os.path.join(target_dir, target_name)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        with open(full_path, "wb") as out:
            out.write(data)
        return f"下载成功：{full_path}"
    except Exception as exc:
        return f"下载失败：真实错误：{type(exc).__name__}: {exc} | URL={url}"
