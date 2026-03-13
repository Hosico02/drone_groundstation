from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QLabel, QPushButton, QSlider, QComboBox, QCheckBox,
                             QFrame, QGridLayout, QSpinBox, QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt

class PIDTuning(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone
        self.initUI()
        
    def initUI(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("PID 调试")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 添加WIKI按钮
        wiki_button = QPushButton("WIKI")
        wiki_button.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: black;
                font-weight: bold;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #FFC107;
            }
        """)
        title_layout.addWidget(wiki_button)
        main_layout.addLayout(title_layout)
        
        # 配置文件选择区域
        config_layout = QHBoxLayout()
        
        # PID配置文件
        pid_profile_label = QLabel("PID 配置文件")
        pid_profile_label.setStyleSheet("color: white;")
        pid_profile_combo = QComboBox()
        pid_profile_combo.addItem("PID 配置文件 1")
        pid_profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        
        # Rate配置文件
        rate_profile_label = QLabel("Rate 配置文件")
        rate_profile_label.setStyleSheet("color: white;")
        rate_profile_combo = QComboBox()
        rate_profile_combo.addItem("Rate 配置文件 1")
        rate_profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        
        config_layout.addWidget(pid_profile_label)
        config_layout.addWidget(pid_profile_combo)
        config_layout.addSpacing(20)
        config_layout.addWidget(rate_profile_label)
        config_layout.addWidget(rate_profile_combo)
        config_layout.addStretch()
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        refresh_button = QPushButton("刷新配置文件")
        copy_rate_button = QPushButton("复制 Rate 配置文件")
        reset_button = QPushButton("重置默认配置文件")
        expert_button = QPushButton("专家模式/PID")
        
        for btn in [refresh_button, copy_rate_button, reset_button, expert_button]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1A73E8;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1557B0;
                }
            """)
        
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(copy_rate_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(expert_button)
        
        # 添加到主布局
        main_layout.addLayout(config_layout)
        main_layout.addLayout(button_layout)
        
        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #444; 
                background: #333;
            }
            QTabBar::tab {
                background: #222;
                color: #aaa;
                padding: 8px 16px;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #333;
                color: white;
            }
        """)
        
        # PID配置页面
        pid_tab = QWidget()
        pid_layout = QVBoxLayout(pid_tab)
        
        # 滑块区域
        sliders_widget = QWidget()
        sliders_layout = QGridLayout(sliders_widget)
        
        # 添加滑块标题
        columns = ["更多稳定", "默认设置", "更多激进"]
        for i, text in enumerate(columns):
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white;")
            sliders_layout.addWidget(label, 0, i+1)
        
        # 添加滑块行
        rows = ["P 控制力度调整系数", "D Term 滤波器系数"]
        for i, text in enumerate(rows):
            # 行标签
            label = QLabel(text)
            label.setStyleSheet("color: white;")
            sliders_layout.addWidget(label, i+1, 0)
            
            # 滑块
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(50)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                               stop:0 #2196F3, stop:0.5 #FFC107, stop:1 #F44336);
                    height: 8px;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: white;
                    width: 16px;
                    height: 16px;
                    margin: -4px 0;
                    border-radius: 8px;
                }
            """)
            sliders_layout.addWidget(slider, i+1, 1, 1, 3)
        
        pid_layout.addWidget(sliders_widget)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        pid_layout.addWidget(line)
        
        # PID和滤波器配置区域
        pid_config_layout = QHBoxLayout()
        
        # 左侧 - PID配置
        left_group = QGroupBox("基础PID 配置文件的高级设置")
        left_group.setStyleSheet("color: white; border: 1px solid #444; padding: 10px;")
        left_layout = QVBoxLayout(left_group)
        
        # PID基本配置
        for name in ["使用PID控制器参数", "PID控制器参数 1"]:
            checkbox = QCheckBox(name)
            checkbox.setStyleSheet("color: white;")
            left_layout.addWidget(checkbox)
        
        # 增加一些滑块作为占位符
        pid_params = ["P", "I", "D"]
        for param in pid_params:
            param_layout = QHBoxLayout()
            label = QLabel(f"{param}:")
            label.setFixedWidth(30)
            label.setStyleSheet("color: white;")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 200)
            slider.setValue(100)
            value_label = QLabel("100")
            value_label.setFixedWidth(30)
            value_label.setStyleSheet("color: white;")
            
            param_layout.addWidget(label)
            param_layout.addWidget(slider)
            param_layout.addWidget(value_label)
            left_layout.addLayout(param_layout)
        
        # 右侧 - D Term配置
        right_group = QGroupBox("D Term 高级设置")
        right_group.setStyleSheet("color: white; border: 1px solid #444; padding: 10px;")
        right_layout = QVBoxLayout(right_group)
        
        # D Term配置
        checkbox = QCheckBox("使用D Term 滤波")
        checkbox.setStyleSheet("color: white;")
        checkbox.setChecked(True)
        right_layout.addWidget(checkbox)
        
        # D Term过滤器设置
        for i in range(1, 3):
            filter_layout = QHBoxLayout()
            filter_label = QLabel(f"D Term 低通滤波 {i}:")
            filter_label.setStyleSheet("color: white;")
            filter_combo = QComboBox()
            filter_combo.addItems(["PT1", "BIQUAD"])
            filter_combo.setStyleSheet("background-color: #444; color: white; border: 1px solid #555;")
            
            filter_layout.addWidget(filter_label)
            filter_layout.addWidget(filter_combo)
            right_layout.addLayout(filter_layout)
            
            # 频率设置
            freq_layout = QHBoxLayout()
            freq_label = QLabel("截止频率 [Hz]:")
            freq_label.setStyleSheet("color: white;")
            freq_spin = QSpinBox()
            freq_spin.setRange(0, 500)
            freq_spin.setValue(100)
            freq_spin.setStyleSheet("background-color: #444; color: white; border: 1px solid #555;")
            
            freq_layout.addWidget(freq_label)
            freq_layout.addWidget(freq_spin)
            right_layout.addLayout(freq_layout)
        
        pid_config_layout.addWidget(left_group)
        pid_config_layout.addWidget(right_group)
        pid_layout.addLayout(pid_config_layout)
        
        # 高级PID设置
        advanced_group = QGroupBox("高级PID配置设置")
        advanced_group.setStyleSheet("color: white; border: 1px solid #444; padding: 10px;")
        advanced_layout = QGridLayout(advanced_group)
        
        advanced_items = [
            {"name": "D微分增益", "value": 100},
            {"name": "P衰减", "value": 0},
            {"name": "I衰减", "value": 100},
            {"name": "最小油门", "value": 1000}
        ]
        
        for i, item in enumerate(advanced_items):
            label = QLabel(item["name"] + ":")
            label.setStyleSheet("color: white;")
            spin = QSpinBox()
            spin.setRange(0, 1000)
            spin.setValue(item["value"])
            spin.setStyleSheet("background-color: #444; color: white; border: 1px solid #555;")
            
            row = i // 2
            col = (i % 2) * 2
            
            advanced_layout.addWidget(label, row, col)
            advanced_layout.addWidget(spin, row, col+1)
        
        pid_layout.addWidget(advanced_group)
        
        # Rate配置页面
        rate_tab = QWidget()
        rate_layout = QVBoxLayout(rate_tab)
        
        # 添加Rate配置内容作为占位符
        rate_layout.addWidget(QLabel("此处将包含Rate配置设置"))
        
        # 滤波器设置页面
        filter_tab = QWidget()
        filter_layout = QVBoxLayout(filter_tab)
        
        # 添加滤波器配置内容作为占位符
        filter_layout.addWidget(QLabel("此处将包含滤波器设置"))
        
        # 添加标签页
        tab_widget.addTab(pid_tab, "PID 配置文件设置")
        tab_widget.addTab(rate_tab, "Rate 配置文件设置")
        tab_widget.addTab(filter_tab, "滤波器设置")
        
        main_layout.addWidget(tab_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #333;
                color: white;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                font-weight: bold;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555;
                background: #333;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #5A5;
                background: #5A5;
            }
        """) 