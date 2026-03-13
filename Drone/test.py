import time
import threading
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink


class DroneFlightModeDetector:
    """无人机飞行模式检测器"""
    def __init__(self, connection_string='/dev/ttyUSB0', baudrate=57600):
        """
        初始化检测器
        :param connection_string: 连接字符串 (如 'COM3', '/dev/ttyUSB0', 'udp:127.0.0.1:14550')
        :param baudrate: 波特率
        """
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.mavlink_connection = None
        self.detected_modes = set()
        self.current_mode = None
        self.running = False

        # ArduPilot飞行模式映射表
        self.flight_modes = {
            0: "STABILIZE",  # 自稳模式
            1: "ACRO",  # 特技模式
            2: "ALT_HOLD",  # 定高模式
            3: "AUTO",  # 自动模式
            4: "GUIDED",  # 引导模式
            5: "LOITER",  # 悬停模式
            6: "RTL",  # 返航模式
            7: "CIRCLE",  # 绕圆模式
            8: "POSITION",  # 位置模式
            9: "LAND",  # 降落模式
            10: "OF_LOITER",  # 光流悬停
            11: "DRIFT",  # 漂移模式
            13: "SPORT",  # 运动模式
            14: "FLIP",  # 翻滚模式
            15: "AUTOTUNE",  # 自动调参
            16: "POSHOLD",  # 位置保持
            17: "BRAKE",  # 刹车模式
            18: "THROW",  # 抛投模式
            19: "AVOID_ADSB",  # 避障模式
            20: "GUIDED_NOGPS",  # 无GPS引导
            21: "SMART_RTL",  # 智能返航
            22: "FLOWHOLD",  # 光流保持
            23: "FOLLOW",  # 跟随模式
            24: "ZIGZAG",  # 之字形模式
            25: "SYSTEMID",  # 系统识别
            26: "AUTOROTATE",  # 自转模式
            27: "AUTO_RTL"  # 自动返航
        }

    def connect(self):
        """连接到无人机"""
        try:
            print(f"正在连接到无人机: {self.connection_string}")

            # 创建MAVLink连接
            self.mavlink_connection = mavutil.mavlink_connection(
                self.connection_string,
                baud=self.baudrate
            )

            print("等待心跳包...")
            # 等待心跳包
            heartbeat = self.mavlink_connection.wait_heartbeat(timeout=10)

            if heartbeat is None:
                print("❌ 连接失败：未收到心跳包")
                return False

            print(f"✅ 连接成功！")
            print(f"   系统ID: {self.mavlink_connection.target_system}")
            print(f"   组件ID: {self.mavlink_connection.target_component}")
            print(f"   自驾仪类型: {heartbeat.autopilot}")
            print(f"   飞行器类型: {heartbeat.type}")

            return True

        except Exception as e:
            print(f"❌ 连接错误: {e}")
            return False

    def start_detection(self, duration=30):
        """
        开始检测飞行模式
        :param duration: 检测持续时间（秒）
        """
        if not self.mavlink_connection:
            print("❌ 请先连接无人机")
            return

        print(f"\n🔍 开始检测飞行模式（持续{duration}秒）...")
        print("💡 请在检测期间切换不同的飞行模式")
        print("-" * 50)

        self.running = True
        start_time = time.time()

        while self.running and (time.time() - start_time) < duration:
            try:
                # 接收消息
                msg = self.mavlink_connection.recv_match(
                    type=['HEARTBEAT', 'SYS_STATUS'],
                    blocking=True,
                    timeout=1
                )

                if msg:
                    self._process_message(msg)

            except Exception as e:
                print(f"⚠️ 接收消息错误: {e}")

        print("\n🏁 检测完成！")
        self._show_results()

    def _process_message(self, msg):
        """处理接收到的消息"""
        msg_type = msg.get_type()

        if msg_type == 'HEARTBEAT':
            # 检查是否有自定义模式
            if hasattr(msg, 'custom_mode'):
                mode_id = msg.custom_mode
                mode_name = self.flight_modes.get(mode_id, f"未知模式_{mode_id}")

                # 如果是新检测到的模式
                if mode_id not in self.detected_modes:
                    self.detected_modes.add(mode_id)
                    print(f"✨ 检测到新模式: {mode_name} (ID: {mode_id})")

                # 更新当前模式
                if self.current_mode != mode_id:
                    self.current_mode = mode_id
                    print(f"🔄 当前模式: {mode_name}")

    def test_mode_switching(self):
        """测试模式切换功能"""
        if not self.mavlink_connection:
            print("❌ 请先连接无人机")
            return

        print("\n🧪 测试模式切换功能...")

        # 测试常用模式
        test_modes = [0, 2, 4, 5, 6]  # STABILIZE, ALT_HOLD, GUIDED, LOITER, RTL

        for mode_id in test_modes:
            mode_name = self.flight_modes.get(mode_id, f"模式_{mode_id}")
            print(f"🔧 尝试切换到: {mode_name}")

            try:
                # 发送模式切换命令
                self.mavlink_connection.mav.set_mode_send(
                    self.mavlink_connection.target_system,
                    mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    mode_id
                )

                # 等待确认
                time.sleep(2)

                # 检查当前模式
                msg = self.mavlink_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=3)
                if msg and hasattr(msg, 'custom_mode'):
                    if msg.custom_mode == mode_id:
                        print(f"✅ 成功切换到: {mode_name}")
                        self.detected_modes.add(mode_id)
                    else:
                        current_name = self.flight_modes.get(msg.custom_mode, f"模式_{msg.custom_mode}")
                        print(f"⚠️ 切换失败，当前模式: {current_name}")
                else:
                    print(f"❌ 无法确认模式切换")

            except Exception as e:
                print(f"❌ 切换模式失败: {e}")

    def get_all_possible_modes(self):
        """获取所有可能的飞行模式"""
        print("\n📋 所有可能的飞行模式:")
        print("-" * 50)

        for mode_id, mode_name in sorted(self.flight_modes.items()):
            status = "✅ 已检测" if mode_id in self.detected_modes else "❓ 未检测"
            print(f"{mode_id:2d}: {mode_name:<15} {status}")

    def _show_results(self):
        """显示检测结果"""
        print("\n📊 检测结果:")
        print("=" * 50)
        print(f"🔢 检测到的飞行模式数量: {len(self.detected_modes)}")

        if self.detected_modes:
            print("\n✅ 您的无人机支持以下飞行模式:")
            for mode_id in sorted(self.detected_modes):
                mode_name = self.flight_modes.get(mode_id, f"未知模式_{mode_id}")
                print(f"   • {mode_name} (ID: {mode_id})")
        else:
            print("❌ 未检测到任何飞行模式")

        print("\n💡 建议:")
        print("   1. 如果检测到的模式较少，请手动切换更多模式")
        print("   2. 确保无人机已解锁且处于安全环境")
        print("   3. 某些模式可能需要特定条件才能激活")

    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.mavlink_connection:
            self.mavlink_connection.close()
            print("🔌 已断开连接")


def main():
    """主函数"""
    print("🚁 无人机飞行模式检测器")
    print("=" * 50)

    # 配置连接参数（请根据您的实际情况修改）
    conn_str = '/dev/ttyUSB0'

    # 创建检测器
    detector = DroneFlightModeDetector(conn_str, 57600)

    try:
        # 连接无人机
        if detector.connect():
            # 显示所有可能的模式
            detector.get_all_possible_modes()
            # 开始检测
            print("\n选择检测方式:")
            print("1. 被动检测（监听模式变化）")
            print("2. 主动测试（尝试切换模式）")
            print("3. 两种方式都用")

            try:
                method = int(input("请选择 (1-3): "))
            except:
                method = 1

            if method in [1, 3]:
                detector.start_detection(30)

            if method in [2, 3]:
                detector.test_mode_switching()

            # 显示最终结果
            detector.get_all_possible_modes()

    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断检测")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
    finally:
        detector.disconnect()


if __name__ == "__main__":
    main()