"""
TrayService - 系统托盘服务

功能：
1. 最小化到系统托盘
2. 托盘菜单（显示/复习/退出）
3. 托盘图标点击恢复窗口
"""

import threading
import time
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

class TrayService:
    def __init__(self, app, on_show_callback, on_review_callback, on_quit_callback):
        """
        初始化托盘服务

        Args:
            app: 主应用实例
            on_show_callback: 显示主窗口的回调
            on_review_callback: 打开复习界面的回调
            on_quit_callback: 退出应用的回调
        """
        self.app = app
        self.on_show = on_show_callback
        self.on_review = on_review_callback
        self.on_quit = on_quit_callback
        self.icon = None
        self.running = False

    def create_icon_image(self):
        """创建托盘图标（绿色书本图标）"""
        # 创建 64x64 图标
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 绘制书本形状
        # 书本底色
        draw.rounded_rectangle(
            [8, 12, 56, 52],
            radius=4,
            fill='#2E7D32'
        )

        # 书脊
        draw.rectangle([30, 12, 34, 52], fill='#1B5E20')

        # 页面线条
        draw.line([18, 22, 26, 22], fill='white', width=2)
        draw.line([18, 30, 26, 30], fill='white', width=2)
        draw.line([18, 38, 26, 38], fill='white', width=2)

        draw.line([38, 22, 46, 22], fill='white', width=2)
        draw.line([38, 30, 46, 30], fill='white', width=2)
        draw.line([38, 38, 46, 38], fill='white', width=2)

        return image

    def create_menu(self):
        """创建托盘菜单"""
        return pystray.Menu(
            item('显示主窗口', self._on_show_clicked, default=True),
            item('立即复习', self._on_review_clicked),
            pystray.Menu.SEPARATOR,
            item('退出', self._on_quit_clicked)
        )

    def _on_show_clicked(self, icon, item):
        """显示主窗口"""
        if self.on_show:
            # 需要在主线程中执行 UI 操作
            self.app.after(0, self.on_show)

    def _on_review_clicked(self, icon, item):
        """打开复习界面"""
        if self.on_review:
            self.app.after(0, self.on_review)

    def _on_quit_clicked(self, icon, item):
        """退出应用"""
        self.stop()
        if self.on_quit:
            self.app.after(0, self.on_quit)

    def start(self):
        """启动托盘图标（在后台线程）"""
        if self.running:
            return

        self.running = True

        def run_tray():
            try:
                self.icon = pystray.Icon(
                    name="VocabBook",
                    icon=self.create_icon_image(),
                    title="智能生词本",
                    menu=self.create_menu()
                )
                self.icon.run()
            except Exception as e:
                print(f"Tray error: {e}")
                self.running = False

        self.tray_thread = threading.Thread(target=run_tray, daemon=True)
        self.tray_thread.start()

    def stop(self):
        """停止托盘图标"""
        self.running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def update_icon_with_badge(self, count):
        """更新图标，显示待复习数量徽章"""
        if not self.icon:
            return

        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 绘制书本
        draw.rounded_rectangle([8, 12, 56, 52], radius=4, fill='#2E7D32')
        draw.rectangle([30, 12, 34, 52], fill='#1B5E20')
        draw.line([18, 22, 26, 22], fill='white', width=2)
        draw.line([18, 30, 26, 30], fill='white', width=2)
        draw.line([38, 22, 46, 22], fill='white', width=2)
        draw.line([38, 30, 46, 30], fill='white', width=2)

        # 如果有待复习，绘制红色徽章
        if count > 0:
            badge_text = str(count) if count < 100 else "99+"
            # 红色圆形背景
            draw.ellipse([40, 0, 64, 24], fill='#F44336')
            # 数字（简单居中）
            text_x = 52 - len(badge_text) * 3
            draw.text((text_x, 4), badge_text, fill='white')

        try:
            self.icon.icon = image
        except Exception:
            pass
