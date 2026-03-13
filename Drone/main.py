import logging
import os
import sys
import serial.tools.list_ports
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, \
    QPushButton, QComboBox, QStatusBar, QDialog, QTextEdit, QMessageBox, QFileDialog
from MAVLink.drone_comm import DroneComm
from control.battery_widget import BatteryWidget
from src.config import setup_logging
from ui.AI_page import AIPage
from ui.cli import CLI
from ui.drone import Drone
# 导入子页面
from ui.home_page import HomePage
from ui.map_page import MapWidget
from ui.modes import Modes
from ui.motors import Motors
from ui.osd import OSD
from ui.pid_tuning import PIDTuning
from ui.receiver import Receiver
from ui.video_page import VideoPage


class GroundStation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地面站")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #333;")

        # 初始化无人机通讯模块
        self.drone = DroneComm(host='', port=57600)
        self.connected = False

        # 连接信号槽
        self.drone.battery_updated.connect(self.on_battery_updated)

        # 设置日志属性
        setup_logging()
        self.logger = logging.getLogger(__name__)

        # 设置主窗口布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建顶部区域
        self.create_header()
        self.create_header2()
        
        # 创建内容区域
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # 创建左侧菜单
        self.create_sidebar()
        
        # 创建内容区域
        self.content_area = QStackedWidget()
        self.content_layout.addWidget(self.content_area)
        
        # 添加内容区域到主布局
        self.main_layout.addWidget(self.content_widget)
        
        # 添加各个页面
        self.setup_pages()

        # 状态栏
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.setStyleSheet("background-color: black; color: white;")
        self.statusbar.showMessage("系统就绪")
        self.logger.info('系统就绪')

        # 连接信号槽
        self.drone.connection_status_changed.connect(self.on_connection_status_changed)

        # 默认显示PID调试页面
        self.content_area.setCurrentIndex(0)  # PID Tuning index
    
    def create_header(self):
        # 创建顶部区域
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(70)
        self.header_widget.setStyleSheet("background-color: #333;")
        
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Logo
        logo_label = QLabel("地面站")
        logo_label.setStyleSheet("""
            color: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:0, 
                stop:0 white, stop:1 white
            );
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            padding: 8px 0 0 0;
            text-shadow: 2px 2px 6px #222;
        """)
        
        # 版本信息
        version_label = QLabel("版本: 0.0.1 (demo)")
        version_label.setStyleSheet("color: #888; font-size: 12px;")
        
        # 添加Logo和版本信息到左侧垂直布局
        logo_layout = QVBoxLayout()
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(version_label)
        
        header_layout.addLayout(logo_layout)
        header_layout.addStretch()
        
        # 添加两个圆形按钮及说明
        left_area = QHBoxLayout()
        left_area.setSpacing(30)
        # 下拉选择框
        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        label_1 = QLabel("串口：")
        label_1.setStyleSheet("background-color: #333; color: white; font-size: 20px; font-weight: bold;")
        label_2 = QLabel("端口号：")
        label_2.setStyleSheet("background-color: #333; color: white; font-size: 20px; font-weight: bold;")
        self.hosts_combobox = QComboBox()
        self.hosts_combobox.setStyleSheet("""
            QComboBox {
                background-color: #222;
                color: white;
                border: 2px solid white;
                border-radius: 8px;
                padding: 2px 10px 2px 10px;
                font-size: 18px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(icons/arrow_down.png);  /* 你可以自定义一个小箭头图标 */
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background: #333;
                color: white;
                border: 1px solid white;
                selection-background-color: #444;
                selection-color: #fff;
            }
        """)
        self.hosts_combobox.setFixedSize(100, 20)
        self.baudrate_combobox = QComboBox()
        self.baudrate_combobox.setStyleSheet("""
            QComboBox {
                background-color: #222;
                color: white;
                border: 2px solid white;
                border-radius: 8px;
                padding: 2px 10px 2px 10px;
                font-size: 18px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(icons/arrow_down.png);  /* 你可以自定义一个小箭头图标 */
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background: #333;
                color: white;
                border: 1px solid white;
                selection-background-color: #444;
                selection-color: #fff;
            }
        """)
        self.baudrate_combobox.setFixedSize(100, 20)
        self.baudrate_combobox.addItem('9600', '9600')
        self.baudrate_combobox.addItem('19200', '19200')
        self.baudrate_combobox.addItem('38400', '38400')
        self.baudrate_combobox.addItem('57600', '57600')
        self.baudrate_combobox.addItem('115200', '115200')
        self.baudrate_combobox.setCurrentText('57600')
        hbox1.addWidget(label_1)
        hbox1.addWidget(self.hosts_combobox)
        hbox2.addWidget(label_2)
        hbox2.addWidget(self.baudrate_combobox)
        self.battery_widget = BatteryWidget(level=0)
        left_area.addWidget(self.battery_widget)
        left_area.addLayout(hbox1)
        left_area.addLayout(hbox2)

        # 第一个按钮保持原样
        vbox0 = QVBoxLayout()
        vbox0.setAlignment(Qt.AlignHCenter)
        self.refresh_button = QPushButton("")
        self.refresh_button.setFixedSize(40, 40)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #ffbb00;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffaa00;
            }
        """)
        label0 = QLabel('刷新串口')
        label0.setStyleSheet("color: white; font-size: 12px;")
        label0.setAlignment(Qt.AlignHCenter)
        vbox0.addWidget(self.refresh_button)
        vbox0.addWidget(label0)
        left_area.addLayout(vbox0)

        vbox1 = QVBoxLayout()
        vbox1.setAlignment(Qt.AlignHCenter)
        btn1 = QPushButton('')
        btn1.setFixedSize(40, 40)
        btn1.setStyleSheet("""
            QPushButton {
                background-color: #ffbb00;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffaa00;
            }
        """)
        label1 = QLabel("更新固件")
        label1.setStyleSheet("color: white; font-size: 12px;")
        label1.setAlignment(Qt.AlignHCenter)
        vbox1.addWidget(btn1)
        vbox1.addWidget(label1)
        left_area.addLayout(vbox1)

        # 第二个按钮为连接/断开
        vbox2 = QVBoxLayout()
        vbox2.setAlignment(Qt.AlignHCenter)
        self.connect_btn = QPushButton("")
        self.connect_btn.setFixedSize(40, 40)
        self.connect_btn.setIcon(QIcon("icons/connect_green.png"))
        self.connect_btn.setIconSize(self.connect_btn.size() * 0.6)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #44cc44;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #33bb33;
            }
        """)
        self.connect_label = QLabel("开始连接")
        self.connect_label.setStyleSheet("color: white; font-size: 12px;")
        self.connect_label.setAlignment(Qt.AlignHCenter)
        vbox2.addWidget(self.connect_btn)
        vbox2.addWidget(self.connect_label)
        left_area.addLayout(vbox2)
        header_layout.addLayout(left_area)
        
        # 将顶部区域添加到主布局
        self.main_layout.addWidget(self.header_widget)
        
        # 连接状态变量
        self.connected = False
        self.connect_btn.clicked.connect(self.connect_drone)
        self.refresh_button.clicked.connect(self.refresh)

    def create_header2(self):
        # 创建次顶部区域，显示日期时间和日志按钮
        self.subheader_widget = QWidget()
        self.subheader_widget.setFixedHeight(30)
        self.subheader_widget.setStyleSheet("background-color: #111;")

        subheader_layout = QHBoxLayout(self.subheader_widget)
        subheader_layout.setContentsMargins(10, 0, 10, 0)

        # 日期时间显示
        self.datetime_label = QLabel()
        self.datetime_label.setStyleSheet("color: #ccc; font-size: 12px;")
        self.update_datetime()

        # 创建定时器更新日期时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)  # 每秒更新一次

        # 日志按钮
        self.log_button = QPushButton("显示日志")
        self.log_button.setStyleSheet("""
                   QPushButton {
                       background-color: #222;
                       color: #ccc;
                       border: none;
                       padding: 3px 10px;
                       font-size: 12px;
                       min-width: 80px;
                   }
                   QPushButton:hover {
                       background-color: #333;
                       color: #fff;
                   }
               """)
        self.log_button.setCursor(Qt.PointingHandCursor)
        self.log_button.clicked.connect(self.show_log_dialog)

        subheader_layout.addWidget(self.datetime_label)
        subheader_layout.addStretch()
        subheader_layout.addWidget(self.log_button)

        # 将次顶部区域添加到主布局
        self.main_layout.addWidget(self.subheader_widget)

    def update_datetime(self):
        # 更新日期时间标签
        current_datetime = QDateTime.currentDateTime()
        formatted_datetime = current_datetime.toString('yyyy-MM-dd HH:mm:ss')
        self.datetime_label.setText(formatted_datetime)
        
    def create_sidebar(self):
        # 创建左侧菜单
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(150)
        self.sidebar_widget.setStyleSheet("background-color: #252525;")
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setSpacing(2)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加菜单项
        self.menu_items = [
            {"name": "首页", "icon": "home.png"},
            {"name": "无人机控制", "icon": "ports.png"},
            {'name': '视频流', 'icon': 'video.png'},
            {'name': '地图', 'icon': 'map.png'},
            {"name": "PID 调试", "icon": "pid.png"},
            {"name": "AI", "icon": "ai.png"},
            {"name": "接收机", "icon": "receiver.png"},
            {"name": "模式", "icon": "modes.png"},
            {"name": "电机", "icon": "motors.png"},
            {"name": "OSD", "icon": "osd.png"},
            {"name": "CLI", "icon": "cli.png"},
        ]
        
        self.menu_buttons = []
        for i, item in enumerate(self.menu_items):
            menu_button = QPushButton(item["name"])
            menu_button.setFixedHeight(40)
            menu_button.setCursor(Qt.PointingHandCursor)
            menu_button.setStyleSheet("""
                QPushButton {
                    background-color: #252525;
                    color: #ccc;
                    border: none;
                    border-left: 3px solid transparent;
                    text-align: left;
                    padding-left: 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #333;
                    color: #fff;
                }
                QPushButton:pressed {
                    background-color: #444;
                    border-left: 3px solid #ffbb00;
                }
            """)
            
            # 默认选中
            if i == 0:
                menu_button.setStyleSheet(menu_button.styleSheet() + """
                    QPushButton {
                        background-color: #444;
                        color: #fff;
                        border-left: 3px solid #ffbb00;
                    }
                """)
            
            menu_button.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            self.menu_buttons.append(menu_button)
            self.sidebar_layout.addWidget(menu_button)
        
        self.sidebar_layout.addStretch()
        self.content_layout.addWidget(self.sidebar_widget)
    
    def switch_page(self, index):
        # 切换页面
        self.content_area.setCurrentIndex(index)
        
        # 更新菜单按钮样式
        for i, button in enumerate(self.menu_buttons):
            if i == index:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #444;
                        color: #fff;
                        border: none;
                        border-left: 3px solid #ffbb00;
                        text-align: left;
                        padding-left: 15px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #333;
                        color: #fff;
                    }
                    QPushButton:pressed {
                        background-color: #444;
                        border-left: 3px solid #ffbb00;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #252525;
                        color: #ccc;
                        border: none;
                        border-left: 3px solid transparent;
                        text-align: left;
                        padding-left: 15px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #333;
                        color: #fff;
                    }
                    QPushButton:pressed {
                        background-color: #444;
                        border-left: 3px solid #ffbb00;
                    }
                """)
        
    def setup_pages(self):
        # 添加各个页面到堆叠窗口
        self.home_page = HomePage(self.drone)
        self.pid_tuning_page = PIDTuning(self.drone)
        self.receiver_page = Receiver(self.drone)
        self.modes_page = Modes(self.drone)
        self.motors_page = Motors(self.drone)
        self.osd_page = OSD(self.drone)
        self.cli_page = CLI(self.drone)
        self.video_page = VideoPage()
        self.map_page = MapWidget(drone=self.drone)
        self.drone_page = Drone(drone=self.drone)
        self.ai_page = AIPage()

        self.content_area.addWidget(self.home_page)
        self.content_area.addWidget(self.drone_page)
        self.content_area.addWidget(self.video_page)
        self.content_area.addWidget(self.map_page)
        self.content_area.addWidget(self.pid_tuning_page)
        self.content_area.addWidget(self.ai_page)
        self.content_area.addWidget(self.receiver_page)
        self.content_area.addWidget(self.modes_page)
        self.content_area.addWidget(self.motors_page)
        self.content_area.addWidget(self.osd_page)
        self.content_area.addWidget(self.cli_page)

    def connect_drone(self):
        # 切换连接状态
        if not self.connected:
            # 保存设置
            host = self.hosts_combobox.currentText().strip()
            baud = int(self.baudrate_combobox.currentData())
            # 更新无人机连接
            self.drone.host = host
            self.drone.port = baud
            # 尝试连接
            self.connect_btn.setEnabled(False)
            self.connect_label.setText("正在连接...")
            # 连接无人机
            if self.drone.connect():
                # self.connect_btn.setIcon(QIcon("icons/disconnect_red.png"))
                self.connect_btn.setStyleSheet("""
                                QPushButton {
                                    background-color: #cc4444;
                                    border-radius: 20px;
                                    border: none;
                                }
                                QPushButton:hover {
                                    background-color: #bb3333;
                                }
                            """)
                self.connect_label.setText("断开连接")
                self.connected = True
            else:
                self.connect_label.setText("重新连接")

            self.connect_btn.setEnabled(True)
        else:
            # self.connect_btn.setIcon(QIcon("icons/connect_green.png"))
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #44cc44;
                    border-radius: 20px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #33bb33;
                }
            """)
            self.connect_label.setText("开始连接")

            self.connected = False

    def refresh(self):
        """刷新串口列表"""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            if ports:
                self.hosts_combobox.addItems(ports)
                self.hosts_combobox.setCurrentText(ports[-1])
            else:
                self.statusbar.showMessage("未找到可用串口")
                self.logger.error("未找到可用串口")
        except ImportError:
            self.statusbar.showMessage("未安装串口工具库，无法自动检测串口")
            self.logger.error("未安装串口工具库，无法自动检测串口")
        except Exception as e:
            self.statusbar.showMessage(f"检测串口时出错: {str(e)}")
            self.logger.error(f"检测串口时出错: {str(e)}")

    def on_connection_status_changed(self, connected, message):
        """处理连接状态变化"""
        self.statusbar.showMessage(message)

    def show_log_dialog(self):
        """弹出对话框显示日志内容"""
        dialog = QDialog(self)
        dialog.setWindowTitle("日志内容")
        dialog.setMinimumSize(800, 600)

        # 主布局
        layout = QVBoxLayout(dialog)

        # 按钮区域
        button_layout = QHBoxLayout()

        # 实时更新开关按钮
        self.auto_refresh_btn = QPushButton("开启实时更新")
        self.auto_refresh_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #44cc44;
                            color: white;
                            border: none;
                            padding: 5px 15px;
                            border-radius: 3px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #33bb33;
                        }
                    """)

        # 清空日志按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.setStyleSheet("""
                QPushButton {
                    background-color: #cc4444;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #bb3333;
                }
            """)

        # 保存日志按钮
        save_btn = QPushButton("保存日志")
        save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffbb00;
                    color: black;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffaa00;
                }
            """)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #666;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #777;
                }
            """)

        # 添加按钮
        button_layout.addWidget(self.auto_refresh_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(save_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        # 文本编辑器
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QTextEdit.NoWrap)
        text_edit.setStyleSheet("background-color: black; color: white;")

        # 初始加载日志内容
        self.log_path = os.path.join(os.getcwd(), 'logs\\data.log')
        self.load_log_content(text_edit)

        # 滚动到最底部显示最新日志
        text_edit.moveCursor(text_edit.textCursor().End)

        # 实时更新定时器
        self.log_timer = QTimer(dialog)
        self.log_timer.timeout.connect(lambda: self.refresh_log_content(text_edit))
        self.auto_refresh_enabled = False

        # 按钮事件连接
        self.auto_refresh_btn.clicked.connect(lambda: self.toggle_auto_refresh(text_edit))
        clear_btn.clicked.connect(lambda: self.clear_log_file(text_edit))
        save_btn.clicked.connect(lambda: self.save_log_to_file(text_edit))
        close_btn.clicked.connect(dialog.accept)

        # 添加到布局
        layout.addLayout(button_layout)
        layout.addWidget(text_edit)

        # 显示对话框
        dialog.exec_()

    def load_log_content(self, text_edit):
        """加载日志内容"""
        try:
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
            else:
                log_content = "日志文件不存在"
        except Exception as e:
            log_content = f"无法读取日志文件: {e}"

        text_edit.setText(log_content)

    def refresh_log_content(self, text_edit):
        """刷新日志内容并保持在底部"""
        # 记录当前是否在底部
        scrollbar = text_edit.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # 重新加载日志内容
        self.load_log_content(text_edit)

        # 如果之前在底部，则保持在底部
        if at_bottom:
            text_edit.moveCursor(text_edit.textCursor().End)

    def toggle_auto_refresh(self, text_edit):
        """切换自动刷新状态"""
        if not self.auto_refresh_enabled:
            # 开启自动刷新
            self.log_timer.start(1000)  # 每秒刷新一次
            self.auto_refresh_enabled = True
            self.auto_refresh_btn.setText("关闭实时更新")
            self.auto_refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #cc4444;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #bb3333;
                }
            """)
            self.statusbar.showMessage("已开启日志实时更新")
        else:
            # 关闭自动刷新
            self.log_timer.stop()
            self.auto_refresh_enabled = False
            self.auto_refresh_btn.setText("开启实时更新")
            self.auto_refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #44cc44;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #33bb33;
                }
            """)
            self.statusbar.showMessage("已关闭日志实时更新")

    def on_battery_updated(self, battery):
        """更新电池电量"""
        self.battery_widget.level = battery

    def clear_log_file(self, text_edit):
        """清空日志文件"""
        reply = QMessageBox.question(
            text_edit.parent(),
            "确认清空",
            "确定要清空日志文件吗？此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 清空日志文件
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    f.write("")

                # 清空文本编辑器显示
                text_edit.clear()

                # 记录清空操作
                self.logger.info("日志文件已被用户清空")
                self.statusbar.showMessage("日志文件已清空")

                # 如果实时更新开启，刷新显示
                if self.auto_refresh_enabled:
                    self.refresh_log_content(text_edit)

            except Exception as e:
                QMessageBox.critical(
                    text_edit.parent(),
                    "错误",
                    f"清空日志文件失败：{str(e)}"
                )
                self.logger.error(f"清空日志文件失败：{str(e)}")

    def save_log_to_file(self, text_edit):
        """保存日志到指定位置"""
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            text_edit.parent(),
            "保存日志文件",
            f"log_backup_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.log",
            "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*.*)"
        )

        if file_path:
            try:
                # 获取当前显示的日志内容
                log_content = text_edit.toPlainText()

                # 保存到指定文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)

                QMessageBox.information(
                    text_edit.parent(),
                    "保存成功",
                    f"日志已保存到：\n{file_path}"
                )

                self.logger.info(f"日志已保存到：{file_path}")
                self.statusbar.showMessage(f"日志已保存到：{os.path.basename(file_path)}")

            except Exception as e:
                QMessageBox.critical(
                    text_edit.parent(),
                    "保存失败",
                    f"保存日志文件失败：{str(e)}"
                )
                self.logger.error(f"保存日志文件失败：{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GroundStation()
    window.show()
    sys.exit(app.exec_()) 