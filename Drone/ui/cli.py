from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QLineEdit, QPushButton


class CLI(QWidget):
    def __init__(self, drone=None, parent=None):
        super().__init__(parent)
        self.drone = drone
        self.init_ui()
        self.command_history = []
        self.history_index = -1

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("background: black; color: #0f0; font-family: Consolas;")
        layout.addWidget(self.output_area)

        hbox = QHBoxLayout()
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("请输入命令...")
        self.input_line.setStyleSheet("background: white; color: black; font-family: Consolas;")
        self.input_line.returnPressed.connect(self.send_command)
        hbox.addWidget(self.input_line)

        self.send_btn = QPushButton("发送", self)
        self.send_btn.clicked.connect(self.send_command)
        hbox.addWidget(self.send_btn)

        layout.addLayout(hbox)

        # 支持上下键切换历史命令
        self.input_line.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.input_line:
            if event.type() == event.KeyPress:
                if event.key() == Qt.Key_Up:
                    if self.command_history and self.history_index > 0:
                        self.history_index -= 1
                        self.input_line.setText(self.command_history[self.history_index])
                        return True
                elif event.key() == Qt.Key_Down:
                    if self.command_history and self.history_index < len(self.command_history) - 1:
                        self.history_index += 1
                        self.input_line.setText(self.command_history[self.history_index])
                        return True
        return super().eventFilter(obj, event)

    def send_command(self):
        cmd = self.input_line.text().strip()
        if cmd:
            self.command_history.append(cmd)
            self.history_index = len(self.command_history)
            self.output_area.append(f"> {cmd}")
            # 这里可以调用实际命令处理逻辑
            result = self.execute_command(cmd)
            self.output_area.append(result)
            self.input_line.clear()

    def execute_command(self, cmd):
        # 这里写实际命令处理逻辑
        # 示例：回显命令
        return f"命令 [{cmd}] 已执行"

