import logging
import sys
import time
import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import vlc

from src.config import setup_logging, Config
from src.fire_detector import Detector


class VideoThreaad(QThread):
    """
    视频处理线程，避免阻塞主UI线程
    """
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = False

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.rtsp_url)

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url)

            self.msleep(30)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class DetectThread(QThread):
    """
    检测线程，负责视频读取和火灾检测
    """
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, video_source, model_path, iou_threshold=0.20, fps=10):
        super().__init__()
        self.video_source = video_source
        self.model_path = model_path
        self.iou_threshold = iou_threshold
        self.fps = fps
        self.running = False

    def run(self):
        self.running = True
        logger = logging.getLogger(__name__)
        logger.info("🚀 启动火灾探测系统")

        try:
            detector = Detector(self.model_path, iou_threshold=self.iou_threshold)
            logger.info(f"加载检测模型： {self.model_path.name}")

            cap = cv2.VideoCapture(str(self.video_source))
            if not cap.isOpened():
                logger.error(f"打开视频源失败: {self.video_source}")
                return
            logger.info(f"处理视频源: {self.video_source}")

            alert_cooldown = Config.ALERT_COOLDOWN
            last_alert_time = 0
            next_detection_to_report = "any"
            last_emit_time = 0

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    logger.info("✅ 视频处理已完成")
                    break

                # 降低分辨率
                frame = cv2.resize(frame, (640, 360))

                # 检测处理
                processed_frame, detection = detector.process_frame(frame)

                # 警报逻辑
                if detection:
                    current_time = time.time()
                    if (next_detection_to_report == "any" or detection == next_detection_to_report) \
                            and (current_time - last_alert_time) > alert_cooldown:
                        logger.warning(f"🐦‍🔥 {detection} 检测！排队警报")
                        last_alert_time = current_time
                        next_detection_to_report = "Smoke" if detection == "Fire" else "Fire"

                # 限制帧率
                now = time.time()
                if now - last_emit_time > 1.0 / self.fps:
                    self.frame_ready.emit(processed_frame)
                    last_emit_time = now

                self.msleep(10)  # 避免CPU占用过高

        except Exception as e:
            logger.critical(f"🚨 关键系统故障: {str(e)}")
        finally:
            if 'cap' in locals():
                cap.release()
            logger.info("🛑 检测线程关闭完成")

    def stop(self):
        self.running = False
        self.wait()


class VideoPage(QWidget):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #222;")
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.rtsp_url = None

        self.init_ui()

        # 创建视频流处理线程
        self.video_thread = VideoThreaad(self.rtsp_url)
        self.video_thread.frame_ready.connect(self.update_frame)

        # 创建检测线程
        self.detect_thread = DetectThread(Config.VIDEO_SOURCE, Config.MODEL_PATH, fps=10)
        self.detect_thread.frame_ready.connect(self.update_frame)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("正在连接视频流...")
        self.video_label.setStyleSheet("background-color: black; color: white;")

        layout.addWidget(self.video_label)

        hbox = QHBoxLayout()
        self.rtsp_input = QLineEdit(self)
        self.rtsp_input.setPlaceholderText("请输入RTSP地址...")
        self.rtsp_input.setStyleSheet("font-size: 14px; padding: 6px; background: white; color: black; border: 1px solid #444;")
        hbox.addWidget(self.rtsp_input)

        self.connect_btn = QPushButton("连接视频流", self)
        self.pause_btn = QPushButton("暂停视频流", self)
        self.close_btn = QPushButton("关闭视频流", self)
        self.connect_btn.setStyleSheet("font-size: 14px; padding: 6px 18px; background: #44cc44; color: #fff; border: none; border-radius: 4px;")
        self.pause_btn.setStyleSheet("font-size: 14px; padding: 6px 18px; background: yellow; color: #fff; border: none; border-radius: 4px;")
        self.close_btn.setStyleSheet("font-size: 14px; padding: 6px 18px; background: red; color: #fff; border: none; border-radius: 4px;")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.start_detection)
        self.pause_btn.clicked.connect(self.pause_detection)
        self.close_btn.clicked.connect(self.close_detection)
        hbox.addWidget(self.connect_btn)
        hbox.addWidget(self.pause_btn)
        hbox.addWidget(self.close_btn)

        layout.addLayout(hbox)

    def connect_stream(self):
        url = self.rtsp_input.text().strip()
        if url:
            media = self.vlc_instance.media_new(url)
            self.player.set_media(media)
            if sys.platform.startswith('linux'):
                self.player.set_xwindow(self.video_frame.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.video_frame.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.video_frame.winId()))
            self.player.play()

    def update_frame(self, frame):
        """更新视频流"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape

        # 转换为QImage
        bytes_per_line = ch * w
        image = QImage(rgb_frame, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # 保持比例缩放图像以适应控件
        scaled_pixmap = QPixmap.fromImage(image).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        """窗口关闭时停止"""
        self.video_thread.stop()
        self.detect_thread.stop()
        super().closeEvent(event)

    def start_detection(self):
        """启动检测线程"""
        self.detect_thread.start()

    def close_detection(self):
        """关闭视频流"""
        self.detect_thread.stop()
        self.video_label.setText("正在连接视频流...")

    def pause_detection(self):
        """暂停视频流"""
        self.detect_thread.stop()