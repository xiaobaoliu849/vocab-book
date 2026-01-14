import os
import sys
import signal

# Prevent app from closing when sending Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal.SIG_IGN)

# 在任何其他导入之前设置 SDL 音频驱动 (修复 Windows 下 pygame 无声问题)
if os.name == 'nt':
    os.environ['SDL_AUDIODRIVER'] = 'directsound'

import customtkinter as ctk
import keyboard
import time
import threading
from PIL import Image

# Add project root to path so imports work if running from inside folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vocab_app.config import load_config, save_config, setup_theme, init_resources, DB_PATH, BASE_DIR, APP_VERSION
from vocab_app.models.database import DatabaseManager
from vocab_app.views.add_view import AddView
from vocab_app.views.list_view import ListView
from vocab_app.views.review_view import ReviewView
from vocab_app.views.settings_view import SettingsView
from vocab_app.views.close_dialog import CloseDialog
from vocab_app.services.tray_service import TrayService
from vocab_app.services.notification_service import NotificationService, ReviewScheduler

class VocabApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Init resources and theme
        init_resources()
        self.config = load_config()
        setup_theme(self.config)

        # Database
        self.db = DatabaseManager(db_path=DB_PATH, json_path=os.path.join(BASE_DIR, 'vocab.json'))
        self.vocab_list = []
        self.reload_vocab_list()

        # Window setup
        word_count = len(self.vocab_list)
        self.title(f"智能生词本 v{APP_VERSION} - {word_count} 个单词")
        self.geometry("1000x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Config state
        self.current_hotkey = self.config.get("hotkey", "ctrl+alt+v")

        # Sidebar
        self.setup_sidebar()

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Views
        self.frames = {}
        self.frames["add"] = AddView(self.main_frame, self)
        self.frames["list"] = ListView(self.main_frame, self)
        self.frames["review"] = ReviewView(self.main_frame, self)
        self.frames["settings"] = SettingsView(self.main_frame, self)

        # Show initial view
        self.show_frame("add")

        # System Tray Service
        self.tray_service = TrayService(
            app=self,
            on_show_callback=self.show_window,
            on_review_callback=lambda: self.show_frame("review"),
            on_quit_callback=self.quit_app
        )
        self.tray_service.start()

        # Notification Service
        self.notification_service = NotificationService(
            on_click_callback=self.show_window
        )

        # Review Reminder Scheduler
        self.review_scheduler = ReviewScheduler(
            db_manager=self.db,
            notification_service=self.notification_service,
            check_interval=1800  # 30分钟检查一次
        )
        self.review_scheduler.start()

        # Global Hotkey
        self.setup_hotkey()

        # App-Local Hotkeys
        self.bind_local_hotkeys()

        # Handle Close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def bind_local_hotkeys(self):
        """Bind app-local shortcuts"""
        self.bind("<Control-n>", lambda e: self.show_frame("add"))
        self.bind("<Control-l>", lambda e: self.show_frame("list"))
        self.bind("<Control-r>", lambda e: self.show_frame("review"))
        self.bind("<Control-s>", lambda e: self.show_frame("settings"))

    def setup_sidebar(self):
        self.is_sidebar_collapsed = self.config.get("sidebar_collapsed", False)
        self.sidebar_width_full = 180
        self.sidebar_width_collapsed = 70
        
        # Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=self.sidebar_width_full if not self.is_sidebar_collapsed else self.sidebar_width_collapsed, corner_radius=0, fg_color=("#f0f0f0", "#1a1a1a"))
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(6, weight=1) # Spacer for bottom settings

        # 1. Collapse Toggle & Logo
        self.logo_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.logo_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(25, 20))
        
        self.btn_collapse = ctk.CTkButton(self.logo_frame, text="≡", width=35, height=35, fg_color="transparent", text_color=("gray20", "gray80"), hover_color=("gray85", "gray25"), font=("Arial", 20, "bold"), command=self.toggle_sidebar)
        self.btn_collapse.pack(side="left")

        self.logo_label = ctk.CTkLabel(self.logo_frame, text="智能生词本", font=ctk.CTkFont(size=20, weight="bold"))
        if not self.is_sidebar_collapsed:
            self.logo_label.pack(side="left", padx=10)

        # 2. Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("add", "🏠", "词汇中心"),
            ("list", "📚", "单词列表"),
            ("review", "🧠", "智能复习")
        ]

        for i, (name, icon, label) in enumerate(nav_items):
            btn = self._create_nav_button(name, icon, label, i + 1)
            self.nav_buttons[name] = btn

        # 3. Settings at bottom
        self.btn_settings = self._create_nav_button("settings", "⚙️", "设置", i + 7) # Use i+7 to put at bottom
        self.nav_buttons["settings"] = self.btn_settings

        if self.is_sidebar_collapsed:
            self.collapse_sidebar_ui()

    def _create_nav_button(self, name, icon, label, row):
        # Activity indicator (Left blue bar)
        indicator = ctk.CTkFrame(self.sidebar_frame, width=4, height=32, corner_radius=2, fg_color="transparent")
        indicator.grid(row=row, column=0, sticky="w", padx=(1, 0), pady=8)
        
        btn = ctk.CTkButton(
            self.sidebar_frame, 
            text=f"{icon}   {label}" if not self.is_sidebar_collapsed else icon,
            width=self.sidebar_width_full-20 if not self.is_sidebar_collapsed else 45,
            height=45,
            corner_radius=8,
            anchor="w" if not self.is_sidebar_collapsed else "center",
            fg_color="transparent",
            text_color=("gray20", "gray80"),
            hover_color=("gray85", "gray25"),
            font=("Microsoft YaHei UI", 14),
            command=lambda n=name: self.show_frame(n)
        )
        btn.grid(row=row, column=0, padx=(10 if not self.is_sidebar_collapsed else 12, 10), pady=8)
        
        btn.indicator = indicator # Store ref
        btn.full_text = f"{icon}   {label}"
        btn.icon_only = icon
        return btn

    def toggle_sidebar(self):
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        self.config["sidebar_collapsed"] = self.is_sidebar_collapsed
        save_config(self.config)
        
        if self.is_sidebar_collapsed:
            self.collapse_sidebar_ui()
        else:
            self.expand_sidebar_ui()

    def collapse_sidebar_ui(self):
        self.sidebar_frame.configure(width=self.sidebar_width_collapsed)
        self.logo_label.pack_forget()
        for name, btn in self.nav_buttons.items():
            btn.configure(text=btn.icon_only, width=45, anchor="center")
            btn.grid_configure(padx=(12, 10))

    def expand_sidebar_ui(self):
        self.sidebar_frame.configure(width=self.sidebar_width_full)
        self.logo_label.pack(side="left", padx=10)
        for name, btn in self.nav_buttons.items():
            btn.configure(text=btn.full_text, width=self.sidebar_width_full-20, anchor="w")
            btn.grid_configure(padx=(10, 10))

    def show_frame(self, name):
        # Hide all frames
        for frame in self.frames.values():
            frame.pack_forget()

        # Update button styles/indicators
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("gray85", "gray25"), text_color=("#3B8ED0", "#3B8ED0"))
                btn.indicator.configure(fg_color="#3B8ED0")
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "gray80"))
                btn.indicator.configure(fg_color="transparent")

        # Show selected frame
        view = self.frames[name]
        view.pack(fill="both", expand=True)
        if hasattr(view, 'on_show'):
            view.on_show()

    def reload_vocab_list(self):
        try:
            self.vocab_list = self.db.get_all_words()
            self.update_title()
        except Exception as e:
            print(f"Error reloading vocab list: {e}")
            self.vocab_list = []

    def update_title(self):
        word_count = len(self.vocab_list)
        self.title(f"智能生词本 v{APP_VERSION} - {word_count} 个单词")

    def setup_hotkey(self):
        try:
            keyboard.unhook_all_hotkeys()
        except (AttributeError, Exception):
            pass
        try:
            keyboard.add_hotkey(self.current_hotkey, self.on_hotkey_triggered)
        except Exception as e:
            print(f"Hotkey setup error: {e}")

    def on_hotkey_triggered(self):
        try:
            keyboard.send('ctrl+c')
            time.sleep(0.1)
        except Exception as e:
            print(f"Auto-copy failed: {e}")
        self.after(0, self.bring_to_front)

    def bring_to_front(self):
        try:
            self.iconify()
            self.deiconify()
            self.state('normal')
            self.attributes('-topmost', True)
            self.lift()
            self.focus_force()
            self.after(200, lambda: self.attributes('-topmost', False))

            self.show_frame("add")
            try:
                clip_text = self.clipboard_get().strip()
                if clip_text and len(clip_text) < 50:
                    add_view = self.frames["add"]
                    if hasattr(add_view, 'entry_word'):
                         current = add_view.entry_word.get().strip()
                         if clip_text.lower() != current.lower():
                             add_view.entry_word.delete(0, "end")
                             add_view.entry_word.insert(0, clip_text)
                             add_view.after(100, add_view.start_search)
            except Exception:
                pass

        except Exception as e:
            print(f"Wake error: {e}")

    def show_window(self):
        """显示主窗口（从托盘恢复）"""
        self.deiconify()
        self.state('normal')
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes('-topmost', False))

    def on_close(self):
        """关闭按钮处理 - 根据配置决定行为"""
        close_action = self.config.get("close_action", "ask")

        if close_action == "minimize":
            # 直接最小化到托盘
            self.minimize_to_tray()
        elif close_action == "exit":
            # 直接退出
            self.quit_app()
        else:
            # 弹出选择对话框
            self.show_close_dialog()

    def show_close_dialog(self):
        """显示关闭行为选择对话框"""
        def on_dialog_result(action, remember):
            if action == "cancel":
                return

            if remember:
                # 保存用户选择
                self.config["close_action"] = action
                save_config(self.config)

            if action == "minimize":
                self.minimize_to_tray()
            elif action == "exit":
                self.quit_app()

        self.close_dialog = CloseDialog(self, on_dialog_result)
        self.wait_window(self.close_dialog)

    def minimize_to_tray(self):
        """最小化到系统托盘"""
        if self.tray_service and self.tray_service.running:
            self.withdraw()
            # 首次最小化时显示提示
            if not hasattr(self, '_tray_notified'):
                self._tray_notified = True
                self.notification_service.notify(
                    "智能生词本",
                    "程序已最小化到系统托盘，双击图标可恢复窗口",
                    duration=3
                )
        else:
            # 托盘服务未运行，直接退出
            self.quit_app()

    def quit_app(self):
        """完全退出应用"""
        # 停止所有后台服务
        try:
            if hasattr(self, 'review_scheduler'):
                self.review_scheduler.stop()
        except Exception as e:
            print(f"Error stopping review scheduler: {e}")
        try:
            if hasattr(self, 'tray_service'):
                self.tray_service.stop()
        except Exception as e:
            print(f"Error stopping tray service: {e}")

        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = VocabApp()
    app.mainloop()
