from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame


class Modes(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 空白页面，仅包含标题
        title = QLabel("飞行模式配置")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setLineWidth(1)
        line.setStyleSheet("background-color: #444;")

        layout.addWidget(title)
        layout.addWidget(line)
        layout.addStretch()
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #333;
                color: white;
            }
        """)

