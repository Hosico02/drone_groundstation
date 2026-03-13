from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class Receiver(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 空白页面，仅包含标题
        title = QLabel("接收机配置")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        
        layout.addWidget(title)
        layout.addStretch()
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #333;
                color: white;
            }
        """) 