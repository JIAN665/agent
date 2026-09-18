import sys
sys.dont_write_bytecode = True   # 禁止 Python 写 __pycache__ 缓存

from installer.dependency_installer import ensure_pyside6

ensure_pyside6()

from PySide6.QtWidgets import QApplication

from ui.main_window import ChatApp
from core.permissions.gate import install_gate
from core.ollama_launcher import ensure_ollama

install_gate()
ensure_ollama()


def main():
    app = QApplication(sys.argv)
    window = ChatApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()