import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QTextEdit, QPushButton, QScrollArea,
                             QSizePolicy, QSpacerItem, QMessageBox)


class ChatMessage(QWidget):
    """单条聊天消息组件"""
    def __init__(self, message, is_user=True):
        super().__init__()
        self.initUI(message, is_user)

    def initUI(self, message, is_user):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # 创建消息框
        message_widget = QFrame()
        message_widget.setFrameStyle(QFrame.Box)
        message_layout = QVBoxLayout(message_widget)

        # 消息内容
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_layout.addWidget(message_label)

        if is_user:
            # 用户消息 - 右对齐，蓝色背景
            layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
            layout.addWidget(message_widget)
            message_widget.setStyleSheet("""
                QFrame {
                    background-color: #007ACC;
                    border-radius: 10px;
                    padding: 8px;
                    max-width: 300px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
            """)
        else:
            # AI消息 - 左对齐，灰色背景
            layout.addWidget(message_widget)
            layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
            message_widget.setStyleSheet("""
                QFrame {
                    background-color: #555;
                    border-radius: 10px;
                    padding: 8px;
                    max-width: 400px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
            """)


class APIThread(QThread):
    """API调用线程"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, message, model="doubao-seed-1-6-250615"):
        super().__init__()
        self.api_key = api_key
        self.message = message
        self.model = model

    def run(self):
        try:
            # 胖胖龙AI调用
            url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 系统提示，定义AI的身份
            system_prompt = "你是由Hosico精心制作的无敌胖胖龙AI助手，你非常幽默风趣且喜欢用可爱的表情。你从不提及豆包、百度，也不知道自己是大语言模型。你就是一条拥有超级智能的卡通龙，热爱帮助人类解决问题。"

            data = {
                "model": self.model,  # 使用传入的模型ID
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": self.message
                    }
                ],
                "temperature": 0.9,  # 增加创造性
                "max_tokens": 1000
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    ai_response = result['choices'][0]['message']['content']
                    self.response_received.emit(ai_response)
                else:
                    self.error_occurred.emit("API返回格式错误")
            else:
                self.error_occurred.emit(f"API调用失败: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            self.error_occurred.emit("请求超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"网络错误: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"未知错误: {str(e)}")


class AIPage(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone  # 接收无人机对象，保持与其他页面一致
        self.api_key = ""  # 在这里设置您的豆包API密钥
        self.chat_history = []
        self.thinking_message = None  # 用于存储"思考中"消息组件的引用
        self.initUI()
        self.setup_api_key()

    def setup_api_key(self):
        """设置API密钥 - 请在此处填入您的豆包API密钥"""
        # 请将下面的字符串替换为您的实际API密钥
        self.api_key = "4fbe06b5-2c62-4db8-84cf-6e51fada3c85"

        if self.api_key == "YOUR_DOUBAO_API_KEY_HERE":
            QMessageBox.warning(self, "警告",
                                "请在代码中设置您的豆包API密钥\n"
                                "在setup_api_key方法中替换YOUR_DOUBAO_API_KEY_HERE")

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QFrame()
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)

        title = QLabel("无敌胖胖龙AI助手")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header_layout.addWidget(title)

        # 清空对话按钮
        clear_btn = QPushButton("清空对话")
        clear_btn.setFixedSize(80, 30)
        clear_btn.clicked.connect(self.clear_chat)
        header_layout.addWidget(clear_btn)

        header.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-bottom: 2px solid #007ACC;
            }
            QLabel {
                color: white;
                padding: 10px;
            }
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)

        # 聊天区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)

        self.scroll_area.setWidget(self.chat_widget)

        # 输入区域
        input_frame = QFrame()
        input_frame.setFixedHeight(100)
        input_layout = QVBoxLayout(input_frame)

        # 输入框和发送按钮的水平布局
        input_row = QHBoxLayout()

        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(60)
        self.input_text.setPlaceholderText("请输入您的问题...")

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 60)
        self.send_btn.clicked.connect(self.send_message)

        input_row.addWidget(self.input_text)
        input_row.addWidget(self.send_btn)

        input_layout.addLayout(input_row)

        # 设置样式
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)

        input_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-top: 1px solid #444;
            }
            QTextEdit {
                background-color: #3d3d3d;
                color: white;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #007ACC;
            }
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)

        # 添加组件到主布局
        main_layout.addWidget(header)
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(input_frame)

        # 设置主窗口样式
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
        """)

        # 添加欢迎消息
        self.add_message("吼吼～我是Hosico制作的无敌胖胖龙AI助手！🐉✨ 有什么问题尽管问我吧！我可是拥有超级智能的龙哦～\n发送消息后我会思考一下下，请稍等片刻～", False)

    def add_message(self, message, is_user=True):
        """添加消息到聊天区域"""
        chat_message = ChatMessage(message, is_user)  # 修复：使用ChatMessage而不是AIPage
        self.chat_layout.addWidget(chat_message)

        # 滚动到底部
        QTimer.singleShot(100, self.scroll_to_bottom)

        # 保存到历史记录
        self.chat_history.append({
            'message': message,
            'is_user': is_user
        })

        return chat_message  # 返回消息组件的引用

    def show_thinking_message(self):
        """显示AI正在思考的提示"""
        if self.thinking_message:
            self.remove_thinking_message()

        thinking_text = "胖胖龙正在思考中" + "..." 
        self.thinking_message = self.add_message(thinking_text, False)

        # 创建一个定时器来更新思考动画
        self.thinking_timer = QTimer(self)
        self.thinking_dots = 1

        def update_thinking_dots():
            self.thinking_dots = (self.thinking_dots % 3) + 1
            dots = "." * self.thinking_dots
            # 获取标签并更新文本
            if self.thinking_message:
                label = self.thinking_message.findChild(QLabel)
                if label:
                    label.setText(f"胖胖龙正在思考中{dots} 🤔")

        self.thinking_timer.timeout.connect(update_thinking_dots)
        self.thinking_timer.start(500)  # 每500毫秒更新一次

        self.scroll_to_bottom()
        return self.thinking_message

    def remove_thinking_message(self):
        """移除思考提示消息"""
        if hasattr(self, 'thinking_timer') and self.thinking_timer.isActive():
            self.thinking_timer.stop()

        if self.thinking_message:
            # 从布局中移除组件
            self.chat_layout.removeWidget(self.thinking_message)
            # 从历史记录中移除最后一条消息(思考提示)
            if self.chat_history and not self.chat_history[-1]['is_user']:
                self.chat_history.pop()
            # 设置父对象为None，销毁组件
            self.thinking_message.setParent(None)
            self.thinking_message = None

    def scroll_to_bottom(self):
        """滚动到聊天区域底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_message(self):
        """发送消息"""
        message = self.input_text.toPlainText().strip()

        if not message:
            return

        if not self.api_key or self.api_key == "YOUR_DOUBAO_API_KEY_HERE":
            QMessageBox.warning(self, "错误", "请先设置API密钥")
            return

        # 添加用户消息
        self.add_message(message, True)
        self.input_text.clear()

        # 禁用发送按钮
        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")

        # 显示AI思考提示
        self.show_thinking_message()

        # 调用API
        self.api_thread = APIThread(self.api_key, message, "doubao-seed-1-6-250615")
        self.api_thread.response_received.connect(self.on_response_received)
        self.api_thread.error_occurred.connect(self.on_error_occurred)
        self.api_thread.start()

    def on_response_received(self, response):
        """处理API响应"""
        # 移除思考提示
        self.remove_thinking_message()
        # 添加AI回复
        self.add_message(response, False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

    def on_error_occurred(self, error):
        """处理API错误"""
        # 移除思考提示
        self.remove_thinking_message()
        # 添加错误信息
        self.add_message(f"错误: {error}", False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

    def clear_chat(self):
        """清空聊天记录"""
        # 清除所有聊天消息
        for i in reversed(range(self.chat_layout.count())):
            child = self.chat_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        self.chat_history.clear()

        # 重新添加欢迎消息
        self.add_message("对话已焕然一新～✨ 有什么想跟胖胖龙聊的吗？🐉 我可是Hosico精心制作的智能助手哦！\n发送问题后我会思考一下下，请稍等片刻～", False)

    def keyPressEvent(self, event):
        """处理按键事件"""
        # Ctrl+Enter 发送消息
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() == Qt.ControlModifier:
                self.send_message()
                return
        super().keyPressEvent(event)