import os
import sys
from pathlib import Path
if getattr(sys, "forzen", False):
    # 打包后：以 exe 所在目录为基准（ollama_home/config/data 都放 exe 旁边）
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = Path(__file__).resolve().parent.parent


def _expand_path(value):
    if value is None:
        return None
    return str(Path(os.path.expandvars(os.path.expanduser(str(value)))).expanduser().resolve())


VOSK_MODEL_DIR = _expand_path(os.environ.get("VOSK_MODEL") or str(BASE_DIR / "vosk_model"))
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5")
OLLAMA_BASE = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL = OLLAMA_BASE + "/api/chat"
BUNDLED_OLLAMA_HOME = str((BASE_DIR / "ollama_home").resolve())
BUNDLED_MODELS_DIR = str((BASE_DIR / "models").resolve())
DEFAULT_OLLAMA_HOME = BUNDLED_OLLAMA_HOME if os.path.exists(BUNDLED_OLLAMA_HOME) or os.path.exists(BUNDLED_MODELS_DIR) else str((Path.home() / ".ollama").resolve())
OLLAMA_HOME = _expand_path(os.environ.get("OLLAMA_HOME") or os.environ.get("OLLAMA_DIR") or DEFAULT_OLLAMA_HOME)
BUNDLED_OLLAMA_EXE = str((BASE_DIR / "ollama.exe").resolve())
# 系统安装的完整版 Ollama（含 llama-server 引擎 + CUDA），优先使用
SYSTEM_OLLAMA_EXE = os.environ.get("OLLAMA_EXE") or r"D:\Ollama\ollama.exe"
USE_BUNDLED_OLLAMA = True   # 保留开关；_find_ollama_exe 改为系统版优先
DOWNLOADS_DIR = str((BASE_DIR / "downloads").resolve())
CLEAR_EACH_TURN = True
ENABLE_WEB_SEARCH = False
USE_BUNDLED_OLLAMA = True
AUTO_COPY_BUNDLED = False
VOICE_ENABLED = True
ASSISTANT_NAME = "澪玖"

# Safety: real local fine-tuning is disabled by default. Set to True only when
# a proper local training toolchain and sufficient resources (GPU, CUDA, etc.)
# are available and you explicitly want to enable in-program training.
ENABLE_REAL_FINETUNE = False

SYSTEM_PROMPT = """你是一个运行在用户本地电脑上的智能助手。
当你需要执行命令时，只输出一个 JSON 对象（不要加其他文字、不要用 Markdown 代码块）：
{"tool": "execute_command", "command": "要执行的命令"}
如果需要联网搜索资料，并且联网搜索已开启，则返回：
{"tool": "search_web", "query": "搜索关键词"}
如果需要下载网络文件或图片，则返回：
{"tool": "download_file", "url": "https://example.com/image.jpg", "filename": "image.jpg", "save_dir": "downloads"}
save_dir 可选，默认是 downloads；如果不提供 filename，可自动从 URL 里提取文件名。
执行完命令后你会看到结果，然后继续完成用户请求。
不需要执行命令时，直接用自然语言回答。
回答要简洁，不要重复你自己说过的话。
如果不能确认结果，必须明确说明“未确认成功”，不要编造完成。"""


def ensure_bundled_runtime_on_path():
    current_path = os.environ.get("PATH", "")
    candidates = [str(BASE_DIR)]
    if os.path.exists(BUNDLED_OLLAMA_HOME):
        candidates.append(BUNDLED_OLLAMA_HOME)
    for folder in candidates:
        if folder and folder not in current_path.split(os.pathsep):
            os.environ["PATH"] = folder + os.pathsep + current_path


ensure_bundled_runtime_on_path()

# 不可更新区：P4/P5 中被系统只读锁保护、程序自身不可修改的路径
IMMUTABLE_DIRS = [
    str(BASE_DIR / "core" / "permissions"),
    str(BASE_DIR / "core" / "updater"),
    str(BASE_DIR / "config" / "sensitive_patterns.json"),
    str(BASE_DIR / "data" / "audit.jsonl"),
    str(BASE_DIR / "data" / "approvals.jsonl"),
]