import threading

from PyQt5.QtCore import QObject, pyqtSignal
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink


class DroneComm(QObject):
    """
    无人机通讯模块，使用MAVLink协议与无人机通讯
    """
    connection_status_changed = pyqtSignal(bool, str)  # 连接状态变化信号(是否连接, 消息)
    position_updated = pyqtSignal(float, float, float) # 位置更新信号(纬度, 经度, 高度)
    battery_updated = pyqtSignal(float) # 更新电池信号
    mission_progress = pyqtSignal(int, int)  # 任务进度信号(当前航点, 总航点数)

    def __init__(self, host='COM3', port=57600):
        """
        初始化无人机通讯模块
        :param host: 串口
        :param port: 端口
        """
        super().__init__()
        self.host = host
        self.port = port

        self.Mavlink = None
        self.connected = False
        self.running = False

        # 模拟位置数据（实际使用时会从无人机获取）
        self.latitude = 30.5928
        self.longitude = 114.3055
        self.altitude = 100.0

    def connect(self):
        """连接到无人机"""
        try:
            if isinstance(self.port, str):
                try:
                    baud_rate = int(self.port)
                except ValueError:
                    baud_rate = 57600
            else:
                baud_rate = self.port

            # 创建MAVLink连接
            self.connection_status_changed.emit(False, f"正在连接: {self.host}:{self.port}")
            self.Mavlink = mavutil.mavlink_connection(
                self.host,
                baud=baud_rate,
            )

            # 等待心跳包
            self.connection_status_changed.emit(False, "等待无人机心跳...")
            heartbeat = self.Mavlink.wait_heartbeat(timeout=10)

            if heartbeat is None:
                self.connection_status_changed.emit(False, "未收到心跳包，连接失败")
                return False

            self.connected = True
            self.connection_status_changed.emit(True, f"已连接到无人机，系统ID: {self.Mavlink.target_system}")

            # 获取无人机状态
            self._request_data_stream()

            # 启动接受线程
            self.running = True
            self.recevie_thread = threading.Thread(target=self._receive_loop)
            self.recevie_thread.daemon = True
            self.recevie_thread.start()

        except Exception as e:
            self.connection_status_changed.emit(False, f"连接失败: {str(e)}")
            return False

    def _request_data_stream(self):
        """请求数据流"""
        if not self.connected or not self.Mavlink:
            return

        # 请求位置信息
        self.Mavlink.mav.request_data_stream_send(
            self.Mavlink.target_system,
            self.Mavlink.target_component,
            mavlink.MAV_DATA_STREAM_POSITION,
            10,
            1
        )
        # 请求扩展状态
        self.Mavlink.mav.request_data_stream_send(
            self.Mavlink.target_system,
            self.Mavlink.target_component,
            mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
            2,  # 2Hz
            1  # 开启
        )
        # 请求任务信息
        self.Mavlink.mav.request_data_stream_send(
            self.Mavlink.target_system,
            self.Mavlink.target_component,
            mavlink.MAV_DATA_STREAM_RAW_CONTROLLER,
            2,  # 2Hz
            1  # 开启
        )

    def _receive_loop(self):
        """接受数据循环"""
        while self.running and self.connected:
            try:
                # 接受MAVLink消息
                msg = self.Mavlink.recv_match(blocking=True)
                if msg:
                    # 处理消息
                    self._process_mavlink_message(msg)
                    self._battery_mavlink_message(msg)
            except Exception as e:
                print(e)
                # 不中断循环，尝试继续接受

    def _process_mavlink_message(self, msg):
        """处理MAVLink消息"""
        msg_type = msg.get_type()
        # 位置信息
        if msg_type == 'GLOBAL_POSITION_INT':
            # 更新位置信息（经度，纬度，高度）
            self.latitude = msg.lat / 1e7
            self.longitude = msg.lon / 1e7
            self.altitude = msg.alt / 1000.0
            self.position_updated.emit(self.latitude, self.longitude, self.altitude)

        # GPS原始信息
        elif msg_type == 'GPS_RAW_INT':
            # 也可以从GPS原始数据中获取位置
            if msg.fix_type >= 2:   # 至少2D定位
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt /1000.0

            # 只有在没有GLOBAL_POSITION_INT消息时更新
            if msg_type == 'GPS_RAW_INT' and (lat != 0 or lon != 0):
                self.latitude = lat
                self.longitude = lon
                self.altitude = alt
                self.position_updated.emit(lat, lon, alt)

    def send_command(self, command, params=None):
        """
        发送MAVLink命令到无人机

        Args:
            command: MAVLink命令ID
            params: 命令参数列表

        Returns:
            bool: 是否成功发送
        """
        if not self.connected or not self.Mavlink:
            return False

        try:
            # 发送命令
            self.Mavlink.mav.command_long_send(
                self.Mavlink.target_system,
                self.Mavlink.target_component,
                command,
                0,  # 确认次数
                *(params or [0] * 7)  # 参数列表，默认7个0
            )
            return True
        except Exception as e:
            self.connection_status_changed.emit(False, f"发送命令失败: {str(e)}")
            print(e)
            return False

    def takeoff(self, altitude=10):
        """
        起飞到指定高度

        Args:
            altitude: 起飞高度（米）
        """
        self.send_command(
            mavlink.MAV_CMD_NAV_TAKEOFF,
            [0, 0, 0, 0, 0, 0, altitude]
        )
        self.connection_status_changed.emit(False, f"已发送起飞命令，目标高度: {altitude}米")

    def land(self):
        """降落"""
        self.send_command(mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, [0] * 7)
        self.connection_status_changed.emit(False, f"已发送降落命令")

    def _battery_mavlink_message(self, msg):
        msg_type = msg.get_type()
        # 处理 SYS_STATUS 消息
        if msg_type == 'SYS_STATUS':
            battery_status = msg.battery_remaing
            if battery_status != 0:
                self.battery_updated.emit(battery_status)

        if msg_type == 'BATTERY_STATUS':
            battery_status = msg.battery_remaing
            if msg.battery_remaing != 0:
                self.battery_updated.emit(battery_status)

    def start_waypoint_mission(self, waypoints, speed, altitude):
        """
            启动航点任务

            Args:
                waypoints: 航点列表，每个航点格式为 (纬度, 经度, 高度)
                speed: 飞行速度 (m/s)
                altitude: 飞行高度 (m)

            Returns:
                bool: 是否成功启动任务
            """

        if not self.connected or not self.Mavlink:
            self.connection_status_changed.emit(False, "未连接到无人机，无法启动任务")
            return False

        if not waypoints:
            self.connection_status_changed.emit(False, "航点列表为空")
            return False

        try:
            # 1. 清除现有任务
            self.Mavlink.mav.mission_clear_all_send(
                self.Mavlink.target_system,
                self.Mavlink.target_component
            )

            # 2. 设置任务项数量
            mission_count = len(waypoints) + 1  # +1 为起飞命令
            self.Mavlink.mav.mission_count_send(
                self.Mavlink.target_system,
                self.Mavlink.target_component,
                mission_count
            )

            # 3. 等待任务请求
            msg = self.Mavlink.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)
            if not msg:
                self.connection_status_changed.emit(False, "未收到任务请求")
                return False

            # 4. 发送起飞命令作为第一个任务项
            self.Mavlink.mav.mission_item_send(
                self.Mavlink.target_system,
                self.Mavlink.target_component,
                0,  # 序号
                mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavlink.MAV_CMD_NAV_TAKEOFF,
                1,  # 当前项
                1,  # 自动继续
                0, 0, 0, 0,  # param1-4
                0, 0,  # x, y (起飞位置使用当前位置)
                10  # z (起飞高度10米)
            )

            # 5. 发送所有航点
            for i, waypoint in enumerate(waypoints):
                lat, lon, alt = waypoint

                # 等待下一个任务请求
                msg = self.Mavlink.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)
                if not msg:
                    self.connection_status_changed.emit(False, f"未收到航点 {i + 1} 的任务请求")
                    return False

                # 发送航点任务项
                self.Mavlink.mav.mission_item_send(
                    self.Mavlink.target_system,
                    self.Mavlink.target_component,
                    i + 1,  # 序号 (起飞是0，航点从1开始)
                    mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavlink.MAV_CMD_NAV_WAYPOINT,
                    0,  # 当前项 (只有第一项设为1)
                    1,  # 自动继续
                    0,  # param1: 在航点停留时间
                    0,  # param2: 接受半径
                    0,  # param3: 穿越半径
                    0,  # param4: 偏航角度
                    lat,  # x: 纬度
                    lon,  # y: 经度
                    alt  # z: 高度
                )

            # 6. 等待任务确认
            msg = self.Mavlink.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            if not msg or msg.type != mavlink.MAV_MISSION_ACCEPTED:
                self.connection_status_changed.emit(False, "任务上传失败")
                return False

             # 7. 设置飞行速度
            if speed > 0:
                self.send_command(
                     mavlink.MAV_CMD_DO_CHANGE_SPEED,
                    [1, speed, -1, 0, 0, 0, 0]  # 地面速度
                )

            # 8. 启动任务
            self.send_command(
                mavlink.MAV_CMD_MISSION_START,
                [0, 0, 0, 0, 0, 0, 0]
            )

            self.connection_status_changed.emit(True, f"航点任务已启动，共 {len(waypoints)} 个航点")
            return True

        except Exception as e:
            self.connection_status_changed.emit(False, f"启动航点任务失败: {str(e)}")
            return False

