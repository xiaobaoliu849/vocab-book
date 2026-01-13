"""
NotificationService - 系统通知服务

功能：
1. Windows 系统通知
2. 点击通知打开应用
"""

import threading
import time

class NotificationService:
    def __init__(self, on_click_callback=None):
        """
        初始化通知服务

        Args:
            on_click_callback: 点击通知时的回调函数
        """
        self.on_click = on_click_callback
        self._toaster = None
        self._init_toaster()

    def _init_toaster(self):
        """初始化 Windows Toast 通知"""
        self._click_supported = False
        try:
            from win10toast_click import ToastNotifier
            self._toaster = ToastNotifier()
            self._click_supported = True
        except ImportError:
            try:
                from win10toast import ToastNotifier
                self._toaster = ToastNotifier()
            except ImportError:
                print("Warning: win10toast not available, notifications disabled")
                self._toaster = None

    def notify(self, title, message, duration=5):
        """
        发送系统通知

        Args:
            title: 通知标题
            message: 通知内容
            duration: 显示时长（秒）
        """
        if not self._toaster:
            print(f"[Notification] {title}: {message}")
            return

        def _show():
            try:
                # 尝试使用带点击回调的版本
                if self._click_supported and self.on_click:
                    self._toaster.show_toast(
                        title,
                        message,
                        duration=duration,
                        threaded=True,
                        callback_on_click=self.on_click
                    )
                else:
                    self._toaster.show_toast(
                        title,
                        message,
                        duration=duration,
                        threaded=True
                    )
            except Exception as e:
                print(f"Notification error: {e}")

        # 在后台线程发送通知
        threading.Thread(target=_show, daemon=True).start()

    def notify_review_reminder(self, count):
        """
        发送复习提醒通知

        Args:
            count: 待复习单词数量
        """
        if count <= 0:
            return

        if count == 1:
            message = "您有 1 个单词待复习，点击开始学习！"
        elif count <= 10:
            message = f"您有 {count} 个单词待复习，现在是复习的好时机！"
        else:
            message = f"您有 {count} 个单词待复习，别让它们溜走！"

        self.notify("📚 智能生词本", message, duration=8)


class ReviewScheduler:
    """复习提醒调度器"""

    def __init__(self, db_manager, notification_service, check_interval=1800):
        """
        初始化调度器

        Args:
            db_manager: 数据库管理器
            notification_service: 通知服务
            check_interval: 检查间隔（秒），默认30分钟
        """
        self.db = db_manager
        self.notifier = notification_service
        self.check_interval = check_interval
        self.running = False
        self._thread = None
        self._last_notified_count = -1
        self._lock = threading.Lock()  # 数据库访问锁

    def start(self):
        """启动调度器"""
        if self.running:
            return

        self.running = True

        def _scheduler_loop():
            # 首次启动延迟 60 秒再检查，避免刚打开就弹通知
            time.sleep(60)

            while self.running:
                try:
                    self._check_and_notify()
                except Exception as e:
                    print(f"Scheduler error: {e}")

                # 等待下一次检查
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

        self._thread = threading.Thread(target=_scheduler_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False

    def _check_and_notify(self):
        """检查待复习单词并发送通知"""
        try:
            # 使用锁保护数据库访问
            with self._lock:
                stats = self.db.get_statistics()
                due_count = stats.get('due_today', 0)

            # 只有当数量变化且有待复习时才通知
            # 避免重复通知同一数量
            if due_count > 0 and due_count != self._last_notified_count:
                self.notifier.notify_review_reminder(due_count)
                self._last_notified_count = due_count

        except Exception as e:
            print(f"Check review error: {e}")

    def force_check(self):
        """强制检查一次（用于测试）"""
        self._last_notified_count = -1
        self._check_and_notify()
