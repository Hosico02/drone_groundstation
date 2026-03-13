import json
import logging
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QTabWidget, QGroupBox, QFormLayout, QPushButton, \
    QInputDialog, QMessageBox
from ui.map_page import MapWidget


class WebChannelBridge(QObject):
    # 定义信号，用于通知其他组件坐标数据变化
    coordinate_added = pyqtSignal(int, float, float)  # index, lat, lng
    coordinate_removed = pyqtSignal(int)  # index
    coordinates_cleared = pyqtSignal()
    coordinates_updated = pyqtSignal(list)  # 完整坐标列表

    def __init__(self):
        super().__init__()
        self.coordinates = {}  # 存储坐标数据 {index: {'lat': lat, 'lng': lng}}

    @pyqtSlot(int, float, float)
    def addCoordinate(self, index, lat, lng):
        """接收JavaScript发送的新坐标"""
        self.coordinates[index] = {'lat': lat, 'lng': lng}
        self.coordinate_added.emit(index, lat, lng)

    @pyqtSlot(int)
    def removeCoordinate(self, index):
        """接收JavaScript发送的删除坐标请求"""
        if index in self.coordinates:
            del self.coordinates[index]
            self.coordinate_removed.emit(index)

    @pyqtSlot()
    def clearAllCoordinates(self):
        """清除所有坐标"""
        self.coordinates.clear()
        self.coordinates_cleared.emit()

    @pyqtSlot(str)
    def updateCoordinateList(self, coordinate_json):
        """接收完整的坐标列表更新"""
        try:
            coordinate_list = json.loads(coordinate_json)
            # 重建坐标字典
            self.coordinates.clear()
            for coord in coordinate_list:
                self.coordinates[coord['index']] = {
                    'lat': coord['lat'],
                    'lng': coord['lng']
                }
            self.coordinates_updated.emit(coordinate_list)
        except json.JSONDecodeError as e:
            print(f"❌ 解析坐标JSON失败: {e}")

    def get_all_coordinates(self):
        """获取所有坐标数据"""
        return dict(self.coordinates)

    def get_coordinate_list(self):
        """获取坐标列表（按索引排序）"""
        return [{'index': idx, 'lat': coord['lat'], 'lng': coord['lng']}
                for idx, coord in sorted(self.coordinates.items())]


class Drone(QWidget):
    def __init__(self, drone=None):
        super().__init__()
        self.drone = drone

        # 设置日志属性
        self.logger = logging.getLogger(__name__)
        # 与Html桥接
        self.web_channel_bridge = WebChannelBridge()
        # 保存标点经纬度
        self.waypoint = []
        # 航点飞行状态
        self.is_mission_running = False
        # 设置样式
        self.setStyleSheet("""
                    QWidget {
                        background-color: #333;
                        color: white;
                    }
                """)
        # 连接信号槽
        self.drone.position_updated.connect(self.on_position_updated)

        # 连接WebChannel桥接信号
        self.web_channel_bridge.coordinate_added.connect(self.coordinate_add)
        self.web_channel_bridge.coordinate_removed.connect(self.coordinate_removed)
        self.web_channel_bridge.coordinates_cleared.connect(self.coordinates_cleared)
        self.web_channel_bridge.coordinates_updated.connect(self.coordinates_updated)

        self.initUI()
        self.setup_webchannel_connection()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("无人机控制")
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
        
        # 地图
        self.map_layout = MapWidget()
        layout.addWidget(self.map_layout)

        # 状态信息组
        status_group = QGroupBox("无人机状态")
        status_layout = QFormLayout()

        self.status_label = QLabel("未连接")
        self.lat_label = QLabel("--")
        self.lng_label = QLabel("--")
        self.alt_label = QLabel("--")

        status_layout.addRow("状态:", self.status_label)
        status_layout.addRow("纬度:", self.lat_label)
        status_layout.addRow("经度:", self.lng_label)
        status_layout.addRow("高度:", self.alt_label)

        # 加载到主页面
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
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

        # 基础飞行控制
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        self.takeoff_btn = QPushButton("起飞")
        self.return_btn = QPushButton("返航")
        self.arm_btn = QPushButton("解锁")
        self.disarm_btn = QPushButton("上锁")
        basic_layout.addWidget(self.takeoff_btn)
        basic_layout.addWidget(self.return_btn)
        basic_layout.addWidget(self.arm_btn)
        basic_layout.addWidget(self.disarm_btn)

        # 无人机编队
        formation_tab = QWidget()
        formation_layout = QVBoxLayout(formation_tab)
        
        formation_layout.addWidget(QLabel("2"))

        # 无人机巡检
        senior_tab = QWidget()
        senior_layout = QVBoxLayout(senior_tab)

        # 航点飞行控制
        waypoint_group = QGroupBox("航点飞行")
        waypoint_layout = QVBoxLayout()

        self.start_mission_btn = QPushButton("开始航点飞行")
        self.pause_mission_btn = QPushButton("暂停任务")
        self.resume_mission_btn = QPushButton("继续任务")
        self.stop_mission_btn = QPushButton("停止任务")

        self.waypoint_count_label = QLabel("航点数量: 0")

        waypoint_layout.addWidget(self.waypoint_count_label)
        waypoint_layout.addWidget(self.start_mission_btn)
        waypoint_layout.addWidget(self.pause_mission_btn)
        waypoint_layout.addWidget(self.resume_mission_btn)
        waypoint_layout.addWidget(self.stop_mission_btn)
        waypoint_group.setLayout(waypoint_layout)

        senior_layout.addWidget(waypoint_group)

        # 添加标签页
        tab_widget.addTab(basic_tab, "基础飞行控制(单机)")
        tab_widget.addTab(formation_tab, "无人机编队")
        tab_widget.addTab(senior_tab, "无人机巡检")
        
        layout.addWidget(tab_widget)

        # 添加连接信号
        self.takeoff_btn.clicked.connect(self.takeoff)
        self.return_btn.clicked.connect(self.land_drone)
        self.arm_btn.clicked.connect(self.arm_drone)
        self.disarm_btn.clicked.connect(self.disarm_drone)

        # 航点飞行信号连接
        self.start_mission_btn.clicked.connect(self.start_waypoint_mission)
        self.pause_mission_btn.clicked.connect(self.pause_mission)
        self.resume_mission_btn.clicked.connect(self.resume_mission)
        self.stop_mission_btn.clicked.connect(self.stop_mission)

        # 初始状态设置
        self.update_mission_buttons()

    def takeoff(self):
        """起飞无人机"""
        altitude, ok = QInputDialog.getDouble(self, "起飞高度", "请输入起飞高度(米):", 10.0, 2.0, 100.0, 1)
        if ok:
            self.drone.takeoff(altitude)

    def land_drone(self):
        """降落无人机"""
        self.drone.land()

    def arm_drone(self):
        """解锁无人机"""
        self.drone.arm_disarm(True)

    def disarm_drone(self):
        """上锁无人机"""
        self.drone.arm_disarm(False)
        
    def on_position_updated(self, lat, lng, alt):
        """处理位置更新"""
        # 更新位置标签
        self.lat_label.setText(f"{lat:.6f}")
        self.lng_label.setText(f"{lng:.6f}")
        self.alt_label.setText(f"{alt:.1f}m")

    def on_mission_progress(self, current_waypoint, total_waypoints):
        """处理任务进度更新"""
        if total_waypoints > 0:
            progress_text = f"{current_waypoint}/{total_waypoints}"
            self.mission_progress_label.setText(f"任务进度: {progress_text}")

        self.logger.info(f"任务进度: {progress_text}")

        # 如果任务完成，重置按钮状态
        if current_waypoint >= total_waypoints:
            self.update_mission_buttons_after_completion()

    def on_mission_status(self, status_message):
        """处理任务状态更新"""
        self.logger.info(f"任务状态: {status_message}")

    def update_mission_buttons_after_completion(self):
        """任务完成后更新按钮状态"""
        self.is_mission_running = False
        self.update_mission_buttons()

    def coordinate_add(self, index, lat, lng):
        """处理新增坐标 - 修复同步问题"""
        self.logger.info(f"✅ Drone收到新坐标: 标点{index} -> ({lat:.6f}, {lng:.6f})")

        # 检查是否已存在相同index的航点，如果存在则更新，否则添加
        existing_waypoint = None
        for i, wp in enumerate(self.waypoint):
            if wp['index'] == index:
                existing_waypoint = i
                break

        if existing_waypoint is not None:
            # 更新现有航点
            self.waypoint[existing_waypoint] = {'index': index, 'lat': lat, 'lng': lng}
        else:
            # 添加新航点
            self.waypoint.append({'index': index, 'lat': lat, 'lng': lng})

        # 按index排序
        self.waypoint.sort(key=lambda x: x['index'])
        self.update_waypoint_display()

    def coordinate_removed(self, index):
        """处理删除坐标 - 修复同步问题"""
        self.logger.info(f"🗑️ Drone收到删除坐标: 标点{index}")

        # 找到并删除对应的航点
        self.waypoint = [wp for wp in self.waypoint if wp['index'] != index]
        self.update_waypoint_display()

    def coordinates_cleared(self):
        """处理清除所有坐标"""
        self.logger.info("🧹 Drone收到清除所有坐标")
        self.waypoint.clear()

    def coordinates_updated(self, coordinate_list):
        """处理坐标列表更新 - 完全同步"""
        self.logger.info(f"🔄 Drone收到坐标列表更新: {len(coordinate_list)}个坐标")

        # 完全重建waypoint列表
        self.waypoint.clear()
        for coord in coordinate_list:
            self.waypoint.append({
                'index': coord['index'],
                'lat': coord['lat'],
                'lng': coord['lng']
            })

        # 按index排序确保顺序正确
        self.waypoint.sort(key=lambda x: x['index'])
        self.update_waypoint_display()

    def update_waypoint_display(self):
        """更新航点显示"""
        pass

    def setup_webchannel_connection(self):
        """设置WebChannel连接"""
        # 将桥接对象传递给MapWidget
        if hasattr(self.map_layout, 'setup_webchannel'):
            self.map_layout.setup_webchannel(self.web_channel_bridge)
        else:
            self.logger.error("⚠️ MapWidget没有setup_webchannel方法")

    def start_waypoint_mission(self):
        """开始航点飞行任务"""
        if not self.waypoint:
            QMessageBox.warning(self, "警告", "请先在地图上设置航点！")
            self.logger.warning("警告！！！请先在地图上设置航点！")
            return

        # 获取飞行高度
        altitude, ok = QInputDialog.getDouble(self, "航点飞行高度", "请输入航点飞行高度(米):", 20.0, 5.0, 100.0, 1)
        self.logger.info(f'航点飞行高度：{altitude}m')
        if not ok:
            return

        # 获取飞行速度
        speed, ok = QInputDialog.getDouble(self, "飞行速度", "请输入飞行速度(m/s):", 5.0, 1.0, 20.0, 1)
        self.logger.info(f'飞行速度：{speed:.1f}m/s')
        if not ok:
            return

        # 准备航点数据
        waypoints = []
        for wp in self.waypoint:
            waypoints.append({
                'lat': wp['lat'],
                'lng': wp['lng'],
                'alt': altitude
            })

        # 发送航点任务
        success = self.drone.start_waypoint_mission(waypoints, speed)
        if success:
            self.is_mission_running = True
            self.update_mission_buttons()
            self.logger.info(f"✅ 开始航点飞行任务，共{len(waypoints)}个航点")
        else:
            QMessageBox.critical(self, "错误", "启动航点飞行任务失败！")
            self.logger.error("启动航点飞行任务失败！")

    def pause_mission(self):
        """暂停任务"""
        success = self.drone.pause_mission()
        if success:
            self.logger.info("⏸️ 任务已暂停")

    def resume_mission(self):
        """继续任务"""
        success = self.drone.resume_mission()
        if success:
            self.logger.info("▶️ 任务已继续")

    def stop_mission(self):
        """停止任务"""
        success = self.drone.stop_mission()
        if success:
            self.is_mission_running = False
            self.update_mission_buttons()
            self.logger.info("⏹️ 任务已停止")

    def update_mission_buttons(self):
        """更新任务控制按钮状态"""
        if self.is_mission_running:
            self.start_mission_btn.setEnabled(False)
            self.pause_mission_btn.setEnabled(True)
            self.resume_mission_btn.setEnabled(True)
            self.stop_mission_btn.setEnabled(True)
        else:
            self.start_mission_btn.setEnabled(len(self.waypoint) > 0)
            self.pause_mission_btn.setEnabled(False)
            self.resume_mission_btn.setEnabled(False)
            self.stop_mission_btn.setEnabled(False)
