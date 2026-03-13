from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout


class HomePage(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone
        # 用于颜色动画
        self.color_position = 0
        # 初始化UI
        self.initUI()

    def initUI(self):
        # 设置整体布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 设置背景图片
        self.setStyleSheet(f"""QWidget#homePage {{background-image: url('icons/preview.jpg'); background-position: center; background-repeat: no-repeat;}}""")
        self.setObjectName("homePage")

        # 标题
        title = QLabel("首页")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")

        main_layout.addWidget(title)
        main_layout.addWidget(line)

        # 添加醒目大字
        self.thank_you_label = QLabel("制作不易，谢谢支持")
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        self.thank_you_label.setFont(font)
        self.thank_you_label.setAlignment(Qt.AlignCenter)
        self.thank_you_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 150); padding: 20px; border-radius: 15px; "
            "color: red;"
        )
        main_layout.addWidget(self.thank_you_label)

        # 添加间隔
        spacer = QLabel()
        spacer.setFixedHeight(20)
        main_layout.addWidget(spacer)

        # 添加收款码
        pay_container = QWidget()
        pay_layout = QHBoxLayout(pay_container)

        wechat_label = QLabel()
        alipay_label = QLabel()
        wechat_pixmap = QPixmap('icons/WeChat收款码.jpg')
        alipay_pixmap = QPixmap('icons/Alipay收款码.jpg')
        scaled_pixmap = wechat_pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_pixmap_1 = alipay_pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        wechat_label.setPixmap(scaled_pixmap)
        alipay_label.setPixmap(scaled_pixmap_1)
        wechat_label.setAlignment(Qt.AlignCenter)
        alipay_label.setAlignment(Qt.AlignCenter)
        wechat_label.setStyleSheet("background-color: white; padding: 10px; border-radius: 10px;")
        alipay_label.setStyleSheet("background-color: white; padding: 10px; border-radius: 10px;")

        pay_layout.addStretch(1)
        pay_layout.addWidget(wechat_label)
        pay_layout.addWidget(alipay_label)
        pay_layout.addStretch(1)

        main_layout.addWidget(pay_container)
        main_layout.addStretch()

        # 设置颜色动画
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_gradient_color)
        self.color_timer.start(25)  # 每50毫秒更新一次颜色

    def update_gradient_color(self):
        # 创建从左到右的颜色渐变动画
        colors = [
            QColor(255, 0, 0),    # 红
            QColor(255, 165, 0),  # 橙
            QColor(255, 255, 0),  # 黄
            QColor(0, 255, 0),    # 绿
            QColor(0, 0, 255),    # 蓝
            QColor(75, 0, 130),   # 靛
            QColor(238, 130, 238) # 紫
        ]

        # 计算当前颜色和下一个颜色
        color_index = int(self.color_position)
        next_color_index = (color_index + 1) % len(colors)
        current_color = colors[color_index]
        next_color = colors[next_color_index]

        # 计算两个颜色之间的插值
        fraction = self.color_position - color_index
        r = int(current_color.red() + fraction * (next_color.red() - current_color.red()))
        g = int(current_color.green() + fraction * (next_color.green() - current_color.green()))
        b = int(current_color.blue() + fraction * (next_color.blue() - current_color.blue()))

        # 使用线性渐变从左到右
        gradient_style = f"color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba({r}, {g}, {b}, 255), stop:1 rgba({b}, {r}, {g}, 255));"
        self.thank_you_label.setStyleSheet(f"background-color: rgba(0, 0, 0, 150); padding: 20px; border-radius: 15px; {gradient_style}")

        # 更新颜色位置
        self.color_position = (self.color_position + 0.05) % len(colors)