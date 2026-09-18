import html
import os
import shutil
import subprocess
import sys
import threading

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget,
                               QProgressBar, QMenu)
from PySide6.QtGui import QAction, QIcon

import core.config as config
from core.tools import handle_model_reply, resolve_approval
from core.ollama_client import detect_local_ai_environment, list_available_ollama_models
from memory.chat_history import clear_chat_history, messages, save_chat_history
from stt.speech_recognition_engine import SR_AVAILABLE, recognize_from_microphone as recognize_via_google
from stt.vosk_engine import VOSK_AVAILABLE, recognize_from_microphone as recognize_via_vosk
from tts.speaker import speak_text
from ui.resources import APP_STYLESHEET
from ui.worker import ChatWorker
from utils.text_utils import escape_html_text


class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.ASSISTANT_NAME} - 本地 AI 助手")
        self.resize(1180, 820)
        self.setMinimumSize(980, 680)
        self.setStyleSheet(APP_STYLESHEET)

        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(22, 16, 22, 16)

        self.title_label = QLabel(config.ASSISTANT_NAME)
        self.title_label.setObjectName("titleLabel")
        top_bar_layout.addWidget(self.title_label, 1)

        right_tools = QHBoxLayout()
        right_tools.setSpacing(12)

        self.web_enabled = QCheckBox("联网搜索")
        self.web_enabled.setChecked(config.ENABLE_WEB_SEARCH)
        self.web_enabled.toggled.connect(self.update_search_state)
        right_tools.addWidget(self.web_enabled)

        # Settings button: contains three secondary menu items
        from PySide6.QtGui import QCursor
        self.settings_menu = QMenu(self)

        # Text-to-Speech toggle action
        self.tts_action = QAction("启用文本朗读 (TTS)", self)
        self.tts_action.setCheckable(True)
        self.tts_action.setChecked(bool(config.VOICE_ENABLED))
        self.tts_action.toggled.connect(self.set_tts_enabled)
        self.settings_menu.addAction(self.tts_action)

        # Select model directory action
        select_model_action = QAction("选择本地模型目录", self)
        select_model_action.triggered.connect(self.select_model_dir)
        self.settings_menu.addAction(select_model_action)

        # Install voice dependencies action
        install_action = QAction("安装语音依赖", self)
        install_action.triggered.connect(self.install_voice_dependencies)
        self.settings_menu.addAction(install_action)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(lambda: self.settings_menu.exec_(QCursor.pos()))
        right_tools.addWidget(self.settings_btn)

        self.install_progress = QProgressBar()
        self.install_progress.setMinimum(0)
        self.install_progress.setMaximum(100)
        self.install_progress.setValue(0)
        self.install_progress.setVisible(False)
        self.install_progress.setFixedWidth(180)
        right_tools.addWidget(self.install_progress)

        self.new_chat_btn = QPushButton("新会话")
        self.new_chat_btn.clicked.connect(self.clear_chat)
        right_tools.addWidget(self.new_chat_btn)

        top_bar_layout.addLayout(right_tools)
        outer.addWidget(top_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #4b5563; font-size: 12px; margin: 0 2px 4px 2px;")
        outer.addWidget(self.status_label)

        self.chat_busy = False
        self.chat_timeout_timer = None
        self.active_thread = None
        self.active_worker = None

        main_panel = QFrame()
        main_panel.setObjectName("mainPanel")
        panel_layout = QVBoxLayout(main_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)

        self.chat_view = QTextBrowser()
        self.chat_view.setObjectName("chatView")
        self.chat_view.setReadOnly(True)
        self.chat_view.setOpenExternalLinks(True)
        self.chat_view.setTextInteractionFlags(self.chat_view.textInteractionFlags())
        self.chat_view.setUndoRedoEnabled(False)
        self.chat_view.setFocusPolicy(self.chat_view.focusPolicy())
        self.chat_view.setLineWrapMode(QTextBrowser.WidgetWidth)
        panel_layout.addWidget(self.chat_view)

        outer.addWidget(main_panel, 1)

        input_area = QHBoxLayout()
        input_area.setSpacing(10)

        self.input_box = QLineEdit()
        self.input_box.setObjectName("inputField")
        self.input_box.returnPressed.connect(self.send_message)
        input_area.addWidget(self.input_box, 1)

        self.voice_input_btn = QPushButton("🎤 语音输入")
        self.voice_input_btn.clicked.connect(self.start_voice_input)
        input_area.addWidget(self.voice_input_btn)

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        input_area.addWidget(self.send_btn)

        outer.addLayout(input_area)

        self.append_message(config.ASSISTANT_NAME, f"你好，我是 {config.ASSISTANT_NAME}。你可以直接输入问题，也可以让它执行本地命令或搜索内容。", is_user=False)
        self.append_message(config.ASSISTANT_NAME, "本地环境检测：\n" + detect_local_ai_environment(), is_user=False)
        self.append_message(config.ASSISTANT_NAME, "启动检查：\n" + self.bootstrap_local_runtime(), is_user=False)

    def append_message(self, speaker, text, is_user=False):
        plain = str(text or "")
        safe_text = escape_html_text(plain)
        bubble_color = "#dfe9ff" if is_user else "#f0f0f0"
        label = "你" if is_user else speaker
        html_block = (
            f'<div style="margin: 8px 0; padding: 12px 16px; border-radius: 16px; '
            f'background: {bubble_color}; color: #111111; border: 1px solid rgba(17,17,17,0.04);">'
            f'<b>{html.escape(label)}</b><br>{safe_text}</div>'
        )
        self.chat_view.append(html_block)
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def clear_chat(self):
        global messages
        messages = clear_chat_history()
        self.chat_view.clear()
        self.append_message(config.ASSISTANT_NAME, "新会话已开始。", is_user=False)

    def update_search_state(self):
        config.ENABLE_WEB_SEARCH = bool(self.web_enabled.isChecked())

    def update_voice_state(self):
        # kept for backward compatibility but settings menu now controls TTS
        pass

    def set_tts_enabled(self, enabled):
        config.VOICE_ENABLED = bool(enabled)
        state = "已启用" if enabled else "已禁用"
        self.status_label.setText(f"文本朗读 {state}")

    def select_model_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择本地模型目录", os.path.expanduser("~"))
        if not folder:
            return
        folder = os.path.abspath(os.path.expanduser(os.path.expandvars(folder)))
        config.OLLAMA_HOME = folder
        models = list_available_ollama_models()
        if models:
            config.MODEL = models[0]
            self.append_message(config.ASSISTANT_NAME, f"已设置本地模型目录：{folder}\n已检测到模型：{', '.join(models[:10])}\n当前 MODEL 已设置为：{config.MODEL}", is_user=False)
        else:
            self.append_message(config.ASSISTANT_NAME, f"已设置本地模型目录：{folder}\n但未检测到可用模型文件，请确认目录结构。", is_user=False)
        self.status_label.setText("已选择本地模型目录")
        self.append_message(config.ASSISTANT_NAME, "启动检查：\n" + self.bootstrap_local_runtime(), is_user=False)

    def bootstrap_local_runtime(self):
        local_ollama = shutil.which("ollama")
        local_home_exists = os.path.exists(config.OLLAMA_HOME)
        bundled_models_exists = os.path.exists(os.path.join(config.BASE_DIR, "models")) or os.path.exists(os.path.join(config.BASE_DIR, "ollama_home"))

        if local_ollama:
            if local_home_exists:
                return f"已检测到本地 Ollama 可执行文件：{local_ollama}，并存在本地模型目录：{config.OLLAMA_HOME}；将使用本机配置。"
            return f"已检测到 Ollama 可执行文件：{local_ollama}，但未检测到本地模型目录：{config.OLLAMA_HOME}；将使用系统 Ollama（不会覆盖用户目录）。"

        if bundled_models_exists:
            used = os.path.join(config.BASE_DIR, "models") if os.path.exists(os.path.join(config.BASE_DIR, "models")) else os.path.join(config.BASE_DIR, "ollama_home")
            return f"未检测到 Ollama 可执行文件，已找到程序内置模型资源：{used}；将使用内置模型（不复制到用户目录）。"

        return "未检测到 Ollama 可执行文件，请安装 Ollama 或把模型资源放到项目目录下的 models/ 或 ollama_home/。"

    def install_voice_dependencies(self):
        if threading.current_thread() is threading.main_thread():
            threading.Thread(target=self.install_voice_dependencies, daemon=True).start()
            return

        self.install_progress.setVisible(True)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
            result = subprocess.run([sys.executable, "-m", "pip", "install", "vosk", "sounddevice", "SpeechRecognition", "PyAudio"], check=False)
            if result.returncode == 0:
                self.append_message(config.ASSISTANT_NAME, "[提示] 语音依赖安装完成。请重启程序以确保新依赖被正确加载。", is_user=False)
            else:
                self.append_message(config.ASSISTANT_NAME, "[提示] PyAudio 安装失败，通常是 Windows 缺少 Microsoft C++ Build Tools。请安装 Visual Studio C++ 构建工具后再试。", is_user=False)
        except Exception as exc:
            self.append_message(config.ASSISTANT_NAME, f"[错误] 安装失败：{exc}", is_user=False)
        finally:
            self.install_progress.setVisible(False)
            self.install_progress.setValue(0)
            self.status_label.setText("就绪")

    def start_voice_input(self):
        if self.chat_busy:
            return
        if VOSK_AVAILABLE:
            threading.Thread(target=self._do_vosk_input, daemon=True).start()
            return
        if SR_AVAILABLE:
            threading.Thread(target=self._do_voice_input, daemon=True).start()
            return
        self.append_message(config.ASSISTANT_NAME, "[提示] 语音识别依赖缺失，正在尝试自动安装。", is_user=False)
        threading.Thread(target=self.install_voice_dependencies, daemon=True).start()

    def _do_voice_input(self):
        QTimer.singleShot(0, lambda: self.status_label.setText("录音中，请讲话..."))
        QTimer.singleShot(0, lambda: self.send_btn.setEnabled(False))
        QTimer.singleShot(0, lambda: self.input_box.setEnabled(False))
        try:
            text = recognize_via_google(language="zh-CN")
            if text:
                QTimer.singleShot(0, lambda t=text: self._on_transcription_ready(t))
            else:
                QTimer.singleShot(0, lambda: self.append_message(config.ASSISTANT_NAME, "[提示] 未识别到有效语音。", is_user=False))
        except Exception as exc:
            QTimer.singleShot(0, lambda: self.append_message(config.ASSISTANT_NAME, f"[提示] 录音失败：{exc}", is_user=False))
        finally:
            QTimer.singleShot(0, lambda: self.send_btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self.input_box.setEnabled(True))
            QTimer.singleShot(0, lambda: self.status_label.setText("就绪"))

    def _do_vosk_input(self):
        QTimer.singleShot(0, lambda: self.status_label.setText("录音中（离线识别），请讲话..."))
        QTimer.singleShot(0, lambda: self.send_btn.setEnabled(False))
        QTimer.singleShot(0, lambda: self.input_box.setEnabled(False))
        try:
            if not os.path.exists(config.VOSK_MODEL_DIR):
                QTimer.singleShot(0, lambda: self.append_message(config.ASSISTANT_NAME, f"[提示] 未找到 Vosk 模型目录：{config.VOSK_MODEL_DIR}", is_user=False))
                threading.Thread(target=self.install_voice_dependencies, daemon=True).start()
                return
            text = recognize_via_vosk(config.VOSK_MODEL_DIR)
            if text:
                QTimer.singleShot(0, lambda t=text: self._on_transcription_ready(t))
            else:
                QTimer.singleShot(0, lambda: self.append_message(config.ASSISTANT_NAME, "[提示] 未识别到有效语音（离线识别）。", is_user=False))
        except Exception as exc:
            QTimer.singleShot(0, lambda: self.append_message(config.ASSISTANT_NAME, f"[提示] Vosk 录音或识别失败：{exc}", is_user=False))
        finally:
            QTimer.singleShot(0, lambda: self.send_btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self.input_box.setEnabled(True))
            QTimer.singleShot(0, lambda: self.status_label.setText("就绪"))

    def _on_transcription_ready(self, text):
        self.input_box.setText(text)
        self.input_box.setFocus()
        self.append_message(config.ASSISTANT_NAME, f"[语音输入] {text}", is_user=False)

    def speak_reply(self, reply):
        if not config.VOICE_ENABLED or not reply:
            return
        threading.Thread(target=speak_text, args=(reply,), daemon=True).start()

    def send_message(self):
        user_input = self.input_box.text().strip()
        if not user_input or self.chat_busy:
            return
        if user_input.lower() in ("exit", "quit", "退出"):
            self.close()
            return

        self.chat_busy = True
        self.send_btn.setEnabled(False)
        self.status_label.setText("正在思考…")
        self.append_message("你", user_input, is_user=True)
        self.input_box.clear()

        if self.chat_timeout_timer is not None:
            self.chat_timeout_timer.stop()
        self.chat_timeout_timer = QTimer(self)
        self.chat_timeout_timer.setSingleShot(True)
        self.chat_timeout_timer.timeout.connect(self.handle_chat_timeout)
        self.chat_timeout_timer.start(30000)

        messages.append({"role": "user", "content": user_input})
        save_chat_history(messages)

        thread = QThread(self)
        worker = ChatWorker(list(messages))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.on_reply_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.active_thread = thread
        self.active_worker = worker
        thread.start()

    def on_reply_ready(self, reply, error):
        if self.chat_timeout_timer is not None:
            self.chat_timeout_timer.stop()
        self.chat_busy = False
        self.send_btn.setEnabled(True)

        if error:
            self.status_label.setText("未响应")
            self.append_message(config.ASSISTANT_NAME, f"[错误] 调用 Ollama 失败：{error}", is_user=False)
            return

        self.process_reply(reply)

    def handle_chat_timeout(self):
        if self.chat_busy:
            self.chat_busy = False
            self.send_btn.setEnabled(True)
            self.status_label.setText("未响应（超时）")
            self.append_message(config.ASSISTANT_NAME, "[提示] 本地模型响应超时，稍后再试或检查 Ollama 是否正常运行。", is_user=False)

    def process_reply(self, reply):
        result = handle_model_reply(reply)
        status = result.get("status")

        # 普通文本回复
        if status == "not_tool":
            self.chat_busy = False
            self.send_btn.setEnabled(True)
            if self.chat_timeout_timer is not None:
                self.chat_timeout_timer.stop()
            self.status_label.setText("已回复")
            self.append_message(config.ASSISTANT_NAME, reply, is_user=False)
            messages.append({"role": "assistant", "content": reply})
            save_chat_history(messages)
            if config.VOICE_ENABLED:
                QTimer.singleShot(50, lambda: self.speak_reply(reply))
            return

        # 工具执行成功
        if status == "ok":
            tool_name = result.get("tool")
            res = result.get("result")
            self.append_message(config.ASSISTANT_NAME, f"[执行 {tool_name}]", is_user=False)
            self.append_message(config.ASSISTANT_NAME, f"[结果] {res}", is_user=False)
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"工具执行结果:\n{res}\n请继续完成用户请求。"})
            save_chat_history(messages)
            self.chat_busy = False
            self.send_btn.setEnabled(True)
            if self.chat_timeout_timer is not None:
                self.chat_timeout_timer.stop()
            self.status_label.setText("已回复")
            return

        # 需要审批
        if status == "needs_approval":
            ticket = result.get("ticket")
            self.append_message(config.ASSISTANT_NAME,
                                f"[待审批] {ticket.get('tool')}｜{ticket.get('reason') or '风险操作'}", is_user=False)
            self._ask_approval(ticket)
            return

        # 被硬黑名单拒绝
        if status == "denied":
            self.append_message(config.ASSISTANT_NAME, f"[已拒绝] {result.get('reason')}", is_user=False)
            self._finish_turn()
            return

        # 未知工具 / 参数错误
        if status == "unknown_tool":
            self.append_message(config.ASSISTANT_NAME,
                                f"[未知工具] 可用：{', '.join(result.get('available', []))}", is_user=False)
            self._finish_turn()
            return

        if status == "error":
            self.append_message(config.ASSISTANT_NAME, f"[错误] {result.get('error')}", is_user=False)
            self._finish_turn()
            return

        # 兜底
        self._finish_turn()

    def _finish_turn(self):
        self.chat_busy = False
        self.send_btn.setEnabled(True)
        if self.chat_timeout_timer is not None:
            self.chat_timeout_timer.stop()
        self.status_label.setText("已回复")

    def _ask_approval(self, ticket):
        from PySide6.QtWidgets import QMessageBox
        detail = (
            f"工具: {ticket.get('tool')}\n"
            f"参数: {ticket.get('params')}\n"
            f"说明: {ticket.get('reasoning') or '（无）'}\n"
            f"风险等级: {ticket.get('risk')}\n"
            f"拦截原因: {ticket.get('reason') or '命中敏感/高风险规则'}"
        )
        box = QMessageBox(self)
        box.setWindowTitle("⚠️ 敏感操作审批")
        box.setText("此操作需要你的批准才能执行")
        box.setInformativeText(detail)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("同意执行")
        box.button(QMessageBox.No).setText("拒绝")
        approved = box.exec_() == QMessageBox.Yes

        result = resolve_approval(ticket["ticket_id"], approved)
        if approved:
            if result.get("status") == "ok":
                self.append_message(config.ASSISTANT_NAME,
                                    f"[已批准并执行] {result.get('tool')}\n{result.get('result')}", is_user=False)
                messages.append({"role": "assistant", "content": ticket.get("reasoning") or "执行批准的操作"})
                messages.append({"role": "user",
                                 "content": f"工具执行结果:\n{result.get('result')}\n请继续完成用户请求。"})
                save_chat_history(messages)
            else:
                self.append_message(config.ASSISTANT_NAME, f"[执行失败] {result}", is_user=False)
        else:
            self.append_message(config.ASSISTANT_NAME, "[已拒绝] 该操作未执行。", is_user=False)
        self._finish_turn()


if __name__ == "__main__":
    app = QApplication([])
    window = ChatApp()
    window.show()
    app.exec()
