import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus
import cv2
import requests
import telegram
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from filelock import FileLock

# Setup environment and logging
PROJECT_ROOT = Path(__file__).parent.parent
ENV = PROJECT_ROOT / '.env'
load_dotenv(ENV, override=True)
logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, config):
        """初始化通知服务"""
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.config = config
        # 为此实例创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._init_services()

    def _init_services(self):
        """初始化并验证通知提供程序"""
        # WhatsApp初始化
        if all([os.getenv("CALLMEBOT_API_KEY"), os.getenv("RECEIVER_WHATSAPP_NUMBER")]):
            self.whatsapp_enabled = True
            self.base_url = "https://api.callmebot.com/whatsapp.php"
            logger.info("WhatsApp 服务已初始化")
        else:
            self.whatsapp_enabled = False
            logger.warning("WhatsApp 警报已禁用：缺少凭据")

        # Telegram初始化
        if token := os.getenv("TELEGRAM_TOKEN"):
            try:
                self.telegram_bot = FlareGuardBot(
                    token, os.getenv("TELEGRAM_CHAT_ID"))
                # 一起运行所有异步初始化
                if not self.loop.is_running():
                    self.loop.run_until_complete(self._init_telegram())
            except Exception as e:
                logger.error(f"Telegram 安装失败: {e}")
                self.telegram_bot = None
        else:
            logger.info("Telegram 警报已禁用：缺少令牌")


    async def _init_telegram(self):
        """为Telegram进行异步初始化"""
        await self.telegram_bot.initialize()
        logger.info("Telegram 服务已初始化")

    def save_frame(self, frame) -> Path:
        """保存带有时间戳的检测帧"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        filename = self.config.DETECTED_FIRES_DIR / f'alert_{timestamp}.jpg'
        cv2.imwrite(str(filename), frame)
        return filename

    def upload_image(self, image_path: Path) -> str:
        """上传图片到Imgur CDN"""
        try:
            response = requests.post(
                'https://api.imgur.com/3/upload',
                headers={
                    'Authorization': f'客户端ID {self.config.IMGUR_CLIENT_ID}'},
                files={'image': image_path.open('rb')},
                timeout=10
            )
            response.raise_for_status()
            return response.json()['data']['link']
        except Exception as e:
            logger.error(f"图像上传失败: {str(e)}")
            return None

    def send_alert(self, frame, detection: str = "Fire") -> bool:
        """非阻塞警报调度"""
        image_path = self.save_frame(frame)

        # 提交到后台线程
        future = self.executor.submit(
            self._send_alerts_async,
            image_path,
            detection
        )

        # 记录回调时出错
        future.add_done_callback(
            lambda f: f.exception() and logger.error(
                f"警报错误: {f.exception()}")
        )

        return True  # Immediate success assumption

    def _send_alerts_async(self, image_path, detection):
        """后台警报处理"""
        if self.whatsapp_enabled:
            self._send_whatsapp_alert(image_path, detection)
        if self.telegram_bot:
            self._send_telegram_alert(image_path, detection)

    def _send_whatsapp_alert(self, image_path, detection):
        """处理WhatsApp通知流"""
        image_url = self.upload_image(image_path)
        if not image_url:
            logger.error("跳过WhatsApp警报：图像上传失败")
            return False

        message = f"🚨 {detection} Detected! View at {image_url}"
        encoded_msg = quote_plus(message)
        url = f"{self.base_url}?" \
            f"phone={os.getenv('RECEIVER_WHATSAPP_NUMBER')}&" \
            f"text={encoded_msg}&" \
            f"apikey={os.getenv('CALLMEBOT_API_KEY')}"

        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            logger.info("WhatsApp警报已送达")
            return True
        logger.warning(
            f"WhatsApp警报尝试失败：HTTP {response.status_code}")
        return False

    def _send_telegram_alert(self, image_path, detection):
        """通过适当的循环管理处理电报通知"""
        try:
            if not self.loop.is_running():
                asyncio.set_event_loop(self.loop)
                return self.loop.run_until_complete(
                    self.telegram_bot.send_alert(
                        image_path=image_path,
                        caption=f"🚨 {detection} Detected!"))
            return True
        except Exception as e:
            logger.error(f"Telegram 警报失败： {str(e)}")
            return False

    def send_test_message(self):
        """验证系统连接"""
        success = False
        if self.whatsapp_enabled:
            test_msg = "🔧 系统测试：火灾探测系统运行"
            success = self._send_callmebot_message(test_msg)
        if self.telegram_bot:
            try:
                test_image = Path(PROJECT_ROOT, 'data', "test_image.png")
                success |= self.loop.run_until_complete(
                    self.telegram_bot.send_test_alert(test_image))
            except Exception as e:
                logger.error(f"Telegram 测试失败: {e}")
                success = False
        return success

    def _send_callmebot_message(self, message: str) -> bool:
        """核心WhatsApp消息发送者"""
        encoded_msg = quote_plus(message)
        url = f"{self.base_url}?" \
            f"phone={os.getenv('RECEIVER_WHATSAPP_NUMBER')}&" \
            f"text={encoded_msg}&" \
            f"apikey={os.getenv('CALLMEBOT_API_KEY')}"

        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            logger.info("WhatsApp警报已送达")
            return True
        logger.warning(
            f"WhatsApp警报尝试失败：HTTP {response.status_code}")
        return False

    def cleanup(self):
        """适当清理资源"""
        try:
            self.executor.shutdown(wait=True)
            if hasattr(self, 'loop') and not self.loop.is_closed():
                # 取消所有待处理的任务
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
                # 最后一次运行循环以完成取消
                self.loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self.loop), return_exceptions=True))
                self.loop.close()
        except Exception as e:
            logger.error(f"清理错误: {str(e)}")

    def __del__(self):
        """确保已调用清理"""
        self.cleanup()


class FlareGuardBot:
    def __init__(self, token: str, default_chat_id: str = None):
        self.logger = logging.getLogger(__name__)
        self.token = token
        self.default_chat_id = default_chat_id
        self.bot = telegram.Bot(token=self.token)
        self._init_crypto()
        self.storage_file = Path(__file__).parent / "sysdata.bin"
        self.update_file = Path(__file__).parent / "last_update.bin" 
        self.chat_ids = self._load_chat_ids()

    async def initialize(self):
        """异步初始化序列"""
        await self._update_chat_ids()

    def _init_crypto(self):
        """初始化加密系统"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("需要ENCRYPTION_KEY环境变量")
        self.cipher_suite = Fernet(key.encode())

    def _load_chat_ids(self):
        """通过文件锁定从安全存储中加载加密的聊天ID"""
        try:
            if self.storage_file.exists():
                with FileLock(str(self.storage_file) + ".lock"):
                    self.storage_file.chmod(0o600)
                    with open(self.storage_file, "rb") as f:
                        encrypted_data = f.read()
                        decrypted = self.cipher_suite.decrypt(encrypted_data)
                        ids = json.loads(decrypted)
                        if not all(isinstance(i, int) for i in ids):
                            raise ValueError("聊天ID格式无效")
                        return list(set(ids))  # 删除重复项
            return []
        except Exception as e:
            self.logger.error(f"未能加载聊天ID: {e}")
            return []

    def _save_chat_ids(self):
        """通过加密和文件锁定安全存储聊天ID"""
        try:
            with FileLock(str(self.storage_file) + ".lock"):
                encrypted = self.cipher_suite.encrypt(
                    json.dumps(list(set(self.chat_ids))).encode()
                )
                with open(self.storage_file, "wb") as f:
                    f.write(encrypted)
                self.storage_file.chmod(0o600)
        except Exception as e:
            self.logger.error(f"保存聊天ID失败： {e}")

    def _get_last_update_id(self):
        """获取上次处理的更新的加密ID"""
        try:
            if self.update_file.exists():
                with FileLock(str(self.update_file) + ".lock"):
                    self.update_file.chmod(0o600)
                    with open(self.update_file, "rb") as f:
                        encrypted_data = f.read()
                        decrypted = self.cipher_suite.decrypt(encrypted_data)
                        return int(decrypted.decode())
        except Exception as e:
            self.logger.error(f"未能读取上次更新ID: {e}")
        return 0

    def _save_last_update_id(self, update_id: int):
        """保存上次处理的更新的加密ID"""
        try:
            with FileLock(str(self.update_file) + ".lock"):
                encrypted = self.cipher_suite.encrypt(str(update_id).encode())
                with open(self.update_file, "wb") as f:
                    f.write(encrypted)
                self.update_file.chmod(0o600)
        except Exception as e:
            self.logger.error(f"未能保存上次更新ID: {e}")

    async def _update_chat_ids(self):
        """通过偏移处理安全地发现和存储新的聊天ID"""
        try:
            offset = self._get_last_update_id()
            updates = await self.bot.get_updates(offset=offset + 1, timeout=30)

            new_ids = []
            for update in updates:
                if update.message and update.message.chat_id:
                    chat_id = update.message.chat_id
                    if chat_id not in self.chat_ids:
                        new_ids.append(chat_id)
                        self.chat_ids.append(chat_id)
                        self.logger.info(f"已注册新聊天ID: {chat_id}")

                # 将偏移量更新为最新处理的更新
                if update.update_id >= offset:
                    offset = update.update_id
                    self._save_last_update_id(offset)

            if new_ids:
                self._save_chat_ids()
                self.logger.info(f"保存 {len(new_ids)} 新聊天IDs")
        except Exception as e:
            self.logger.error(f"聊天ID更新失败： {e}")

    async def _verify_chat_id(self, chat_id: int) -> bool:
        """验证聊天ID是否仍然有效"""
        try:
            await self.bot.send_chat_action(chat_id=chat_id, action="typing")
            return True
        except telegram.error.Unauthorized:
            return False
        except Exception:
            # 对于其他错误，假设聊天仍然有效
            return True

    async def cleanup_invalid_chats(self):
        """从存储中删除无效的聊天ID"""
        invalid_ids = []
        for chat_id in self.chat_ids:
            if not await self._verify_chat_id(chat_id):
                invalid_ids.append(chat_id)
                self.logger.info(f"删除无效的聊天ID: {chat_id}")

        if invalid_ids:
            self.chat_ids = [
                id for id in self.chat_ids if id not in invalid_ids]
            self._save_chat_ids()

    async def send_alert(self, image_path: Path, caption: str) -> bool:
        """使用重试逻辑和无效聊天清理向所有已注册的聊天发送警报"""
        if not image_path.exists():
            self.logger.error(f"警报图像丢失: {image_path}")
            return False

        overall_success = False
        failed_chats = []

        # 读取图像数据一次
        with open(image_path, 'rb') as f:
            image_data = f.read()

        try:
            for chat_id in self.chat_ids:
                sent = False
                for attempt in range(3):
                    try:
                        # 为每次发送尝试创建新的BytesIO
                        photo = BytesIO(image_data)
                        photo.name = 'image.jpg'  # Telegram 需要一个名称

                        async with self.bot:  # 为每个聊天创建新会话
                            await self.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption=caption,
                                parse_mode='Markdown',
                                pool_timeout=20
                            )
                        self.logger.info(
                            f"向Telegram发送提醒，与 {chat_id} 聊天")
                        sent = True
                        overall_success = True
                        break
                    except telegram.error.Unauthorized:
                        self.logger.warning(f"未经授权与 {chat_id} 聊天")
                        failed_chats.append(chat_id)
                        break
                    except telegram.error.TimedOut:
                        await asyncio.sleep(2 ** attempt)
                        self.logger.warning(
                            f"发送给 {chat_id} 超时, 重试 {attempt+1}/3")
                    except telegram.error.NetworkError:
                        await asyncio.sleep(5)
                        self.logger.warning(
                            f"{chat_id} 出现网络错误, 重试 {attempt+1}/3")
                    except Exception as e:
                        self.logger.error(
                            f"发送给 {chat_id} 失败: {str(e)}")
                        if attempt == 2:  # 仅在所有重试后添加失败的聊天记录
                            failed_chats.append(chat_id)
                        break

                if not sent:
                    failed_chats.append(chat_id)

            # 发送提醒后清理无效聊天记录
            if failed_chats:
                self.chat_ids = [
                    id for id in self.chat_ids if id not in failed_chats]
                self._save_chat_ids()
                self.logger.info(
                    f"删除 {len(failed_chats)} 个无效的聊天ID")

        except Exception as e:
            self.logger.error(f"Telegram 错误: {str(e)}")

        return overall_success

    async def send_test_alert(self, test_image: Path):
        """测试警报的特殊方法"""
        return await self.send_alert(test_image, "🔧 系统测试：服务运行")
