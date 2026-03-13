import logging
import os
from pathlib import Path
import sys
import io

PROJECT_ROOT = Path(__file__).parent.parent

def setup_logging():
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 设置编码为UTF-8
    logging.basicConfig(
        filename=log_dir / 'data.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8'  # 添加UTF-8编码支持
    )

    # 同时登录到控制台
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # formatter = logging.Formatter(
    #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # console_handler.setFormatter(formatter)
    # logging.getLogger().addHandler(console_handler)

    # 设置默认编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# 环境变量配置
class Config:
    RECEIVER_WHATSAPP_NUMBER = os.getenv('RECEIVER_WHATSAPP_NUMBER')
    IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')

    MODEL_PATH = PROJECT_ROOT / 'models' / 'best_nano.pt'
    VIDEO_SOURCE = PROJECT_ROOT / 'gen_fire.mp4'
    DETECTED_FIRES_DIR = PROJECT_ROOT / 'detected_fires'

    ALERT_COOLDOWN = 45  # 警报之间的秒数

    @classmethod
    def validate(cls):
        missing_vars = []
        for var in cls.__dict__:
            if not var.startswith('__') and getattr(cls, var) is None:
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"缺少环境变量： {', '.join(missing_vars)}")

        # 创建必要的目录
        cls.DETECTED_FIRES_DIR.mkdir(exist_ok=True)

        if not cls.VIDEO_SOURCE.exists():
            raise FileNotFoundError(
                f"视频源缺失： {cls.VIDEO_SOURCE}")
