import cv2
import numpy as np
from ultralytics import YOLO
import cvzone
import logging
from pathlib import Path
from typing import Tuple, Optional


class Detector:
    def __init__(
        self,
        model_path: Path,
        target_height: int = 640,
        iou_threshold: float = 0.2,
        min_confidence: float = 0.5,
        smoke_confidence: float = 0.75
        ):
        """
        使用YOLO模型初始化火灾探测器

        Args:
            model_path (Path): 模型地址
            target_height (int): 目标高
            iou_threshold (float): 非最大抑制的IOU阈值
            min_confidence (float): 检测的最小置信阈值
        """
        self.logger = logging.getLogger(__name__)

        try:
            self.model = YOLO(str(model_path))
            self.target_height = target_height
            self.iou_threshold = iou_threshold
            self.min_confidence = min_confidence
            self.smoke_confidence = smoke_confidence
            self.names = self.model.model.names

            # 为不同类别定义颜色
            self.colors = {
                "fire": (0, 0, 255),
                "smoke": (128, 128, 128)
            }

            self.logger.info("火灾探测器初始化成功")
        except Exception as e:
            self.logger.error(f"初始化火灾探测器失败： {e}")
            raise

    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        调整大小，保持纵横比

        Args:
            frame (np.ndarray): 输入

        Returns:
            np.ndarray: 调整大小
        """
        height, width = frame.shape[:2]
        aspect_ratio = width / height
        new_width = int(self.target_height * aspect_ratio)
        return cv2.resize(frame, (new_width, self.target_height))

    def draw_detection(self, frame: np.ndarray, box: np.ndarray, class_name: str, confidence: float) -> None:
        """
        在框架上绘制单个检测，增强可视化效果

        Args:
            frame (np.ndarray): 输入
            box (np.ndarray): 检测框坐标 [x1, y1, x2, y2]
            class_name (str): 检测到类别
            confidence (float): 检测置信度
        """
        x1, y1, x2, y2 = box
        # 如果未找到类，则默认为绿色
        color = self.colors.get(class_name.lower(), (0, 255, 0))

        # 计算文本大小以获得更好的定位
        text = f"{class_name}: {confidence:.2f}"

        # 如果标签位置太靠近顶部边缘，请调整标签位置
        label_height = 30  # 标签的大致高度
        if y1 < label_height:
            text_y = y2 + label_height  # 将标签放在方框下面
            rect_y = y2
        else:
            text_y = y1 - 5  # 将标签放在方框上方
            rect_y = y1

        # 为框绘制半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2),
                      color, -1)  # 填充矩形
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0,
                        frame)  # 透明效果

        # 绘制框轮廓
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # 添加方框角以提高可见性
        corner_length = 20
        thickness = 2
        # 左上
        cv2.line(frame, (x1, y1), (x1 + corner_length, y1), color, thickness)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_length), color, thickness)
        # 右上
        cv2.line(frame, (x2, y1), (x2 - corner_length, y1), color, thickness)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_length), color, thickness)
        # 左下
        cv2.line(frame, (x1, y2), (x1 + corner_length, y2), color, thickness)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_length), color, thickness)
        # 右下
        cv2.line(frame, (x2, y2), (x2 - corner_length, y2), color, thickness)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_length), color, thickness)

        # 添加具有增强可见性的检测标签
        cvzone.putTextRect(
            frame,
            text,
            (x1, text_y),
            scale=1.5,
            thickness=2,
            colorR=color,
            colorT=(255, 255, 255),  # 白色字体
            font=cv2.FONT_HERSHEY_SIMPLEX,
            offset=5,
            border=2,
            colorB=(0, 0, 0),  # 黑色方框
        )

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[str]]:
        """
        处理视频帧以检测火灾和烟雾，并增强可视化效果

        Args:
            frame (np.ndarray): 输入

        Returns:
            tuple: (processed_frame, detection: str)
        """
        try:
            frame = self.resize_frame(frame)
            results = self.model(
                frame, iou=self.iou_threshold, conf=self.min_confidence)
            detection = None

            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
                confidences = results[0].boxes.conf.cpu().numpy()

                # 按置信度对检测结果进行排序
                sort_idx = np.argsort(-confidences)  # 降序
                boxes = boxes[sort_idx]
                class_ids = class_ids[sort_idx]
                confidences = confidences[sort_idx]

                for box, class_id, confidence in zip(boxes, class_ids, confidences):
                    class_name = self.names[class_id]

                    # 更新整体检测状态
                    if detection is None:  # 仅在尚未设置时更新
                        if "fire" == class_name.lower() and confidence >= self.min_confidence:
                            detection = "Fire"
                        elif "smoke" == class_name.lower() and confidence >= self.smoke_confidence:
                            detection = "Smoke"

                    self.draw_detection(frame, box, class_name, confidence)

            # 添加帧元数据
            self._add_frame_info(frame, detection)

            return frame, detection

        except Exception as e:
            self.logger.error(f"处理帧时出错： {e}")
            return frame, None

    def _add_frame_info(self, frame: np.ndarray, detection: Optional[str]) -> None:
        """
        添加帧信息叠加

        Args:
            frame (np.ndarray): 输入
            detection (Optional[str]): 当前检测状态
        """
        height, width = frame.shape[:2]

        # 在底部添加半透明覆盖层
        overlay_height = 40
        overlay = frame[height-overlay_height:height, 0:width].copy()
        cv2.rectangle(frame, (0, height-overlay_height),
                      (width, height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.2, frame[height-overlay_height:height, 0:width], 0.8, 0,
                        frame[height-overlay_height:height, 0:width])

        # 添加状态文本
        status_text = f"状态： {detection if detection else '未检测到'}"
        cv2.putText(frame, status_text, (10, height-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 添加置信阈值信息
        conf_text = f"Conf: {self.min_confidence:.2f} | IOU: {self.iou_threshold:.2f}"
        text_size = cv2.getTextSize(
            conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        cv2.putText(frame, conf_text, (width - text_size[0] - 10, height-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
