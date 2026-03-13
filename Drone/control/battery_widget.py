from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt

class BatteryWidget(QWidget):
    def __init__(self, parent=None, level=100):
        super().__init__(parent)
        self.level = level  # 0~100
        self.setFixedSize(50, 24)

    def set_battery_level(self, level):
        self.level = max(0, min(100, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 电池外框
        painter.setPen(Qt.gray)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(2, 2, 40, 20)

        # 电池正极
        painter.setBrush(Qt.gray)
        painter.drawRect(42, 8, 6, 8)

        # 电量填充
        if self.level > 50:
            color = QColor(68, 204, 68)  # 绿色
        elif self.level > 20:
            color = QColor(255, 204, 0)  # 黄色
        else:
            color = QColor(204, 68, 68)  # 红色
        painter.setBrush(color)
        fill_width = int(38 * self.level / 100)
        painter.drawRect(3, 3, fill_width, 18)

        # 百分比文字
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.level}%")