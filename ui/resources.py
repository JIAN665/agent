APP_STYLESHEET = """
QMainWindow {
    background: #f3f2ee;
}
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}
#topBar {
    background: #ffffff;
    border: 1px solid #ece8e3;
    border-radius: 18px;
}
#mainPanel {
    background: #f7f7f7;
    border: 1px solid #e7e3df;
    border-radius: 22px;
}
#chatView {
    background: #f8f9fb;
    color: #1a1a1a;
    border: none;
    border-radius: 20px;
    padding: 12px;
}
#inputField {
    background: #ffffff;
    color: #111111;                      /* ← 加这一行，文字显式设成深色 */
    selection-background-color: #1d1d1f;
    selection-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 12px 16px;
    font-size: 15px;
}
QPushButton {
    background: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 14px;
    padding: 12px 20px;
    font-weight: 600;
}
QPushButton:hover {
    background: #2f2f31;
}
QCheckBox {
    color: #333333;
    font-size: 12px;
}
QLabel#titleLabel {
    color: #111111;
    font-size: 24px;
    font-weight: 700;
}
"""
