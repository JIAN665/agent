import subprocess
import sys


def install_pip_package(package):
    subprocess.run([sys.executable, "-m", "pip", "install", package], check=False)


def ensure_pyside6():
    try:
        import PySide6  # noqa: F401
        return True
    except Exception:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "PySide6"], check=True)
            import PySide6  # noqa: F401
            return True
        except Exception:
            print("[错误] 自动安装 PySide6 失败，请手动运行：python -m pip install PySide6")
            return False


def ensure_voice_dependencies():
    packages = ["SpeechRecognition", "vosk", "sounddevice", "PyAudio"]
    missing = []
    for package in packages:
        try:
            __import__(package)
        except Exception:
            missing.append(package)

    if not missing:
        return True

    try:
        subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=True)
        return True
    except Exception as exc:
        print(f"[错误] 自动安装语音依赖失败：{exc}")
        print("[提示] Windows 下 PyAudio 常因缺少 Microsoft C++ Build Tools 而安装失败；请安装 Visual Studio 2022 的 C++ 构建工具或使用预编译 wheel。")
        return False
