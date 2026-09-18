from PySide6.QtCore import QObject, Signal

from core.ollama_client import chat


class ChatWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, history):
        super().__init__()
        self.history = history

    def run(self):
        try:
            reply = chat(self.history)
            self.finished.emit(reply, None)
        except Exception as exc:
            self.finished.emit(None, str(exc))
