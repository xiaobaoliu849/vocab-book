import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
from PIL import Image
from datetime import datetime, timedelta

from .base_view import BaseView, CTkToolTip
from ..config import SOUNDS_DIR, save_config, BASE_DIR, RESOURCE_DIR, APP_VERSION
from ..services.export_service import ExportService
from ..services.update_service import UpdateService

class SettingsView(BaseView):
    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Main Grid Layout (Sidebar + Content)
        self.grid_columnconfigure(0, weight=0) # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1) # Content expands
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=("gray95", "#212121"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # 2. Content Frame (Container for scrollable canvas)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Setup Scrollable Canvas inside Content Frame
        self.settings_canvas = tk.Canvas(
            self.content_frame,
            bg=self.get_canvas_bg(),
            highlightthickness=0, bd=0
        )
        scrollbar = ctk.CTkScrollbar(self.content_frame, command=self.settings_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.settings_canvas.pack(side="left", fill="both", expand=True)
        self.settings_canvas.configure(yscrollcommand=scrollbar.set)

        self.settings_inner = ctk.CTkFrame(self.settings_canvas, fg_color="transparent")
        self.settings_canvas_window = self.settings_canvas.create_window(
            (0, 0), window=self.settings_inner, anchor="nw"
        )

        self.settings_canvas.bind("<Configure>", self.on_canvas_configure)
        self.settings_canvas.bind("<Enter>", lambda e: self.settings_canvas.bind_all("<MouseWheel>", self.on_mousewheel))
        self.settings_canvas.bind("<Leave>", lambda e: self.settings_canvas.unbind_all("<MouseWheel>"))

        # Category State
        self.current_category = None
        self.category_buttons = {}

        # Setup Sidebar Buttons
        self.create_sidebar_buttons()

        # Initial Load
        self.switch_category("stats")

    def create_sidebar_buttons(self):
        """Create navigation buttons in the sidebar"""
        ctk.CTkLabel(self.sidebar_frame, text="设置选项", font=("Microsoft YaHei UI", 16, "bold"), anchor="w").pack(fill="x", padx=20, pady=(20, 15))

        categories = [
            ("stats", "📊  统计与数据", "查看学习统计、复习热力图和数据管理"),
            ("general", "⚙️  常规设置", "配置快捷键、窗口行为和复习提醒"),
            ("dicts", "📚  词典与外观", "选择词典源和切换主题模式"),
            ("about", "ℹ️  关于软件", "版本信息、检查更新和支持开发者"),
        ]

        for cat_id, text, tooltip in categories:
            btn_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
            btn_container.pack(fill="x", pady=2)

            indicator = ctk.CTkFrame(btn_container, width=3, height=28, corner_radius=2, fg_color="transparent")
            indicator.pack(side="left", padx=(1, 0))

            btn = ctk.CTkButton(
                btn_container,
                text=text,
                height=40,
                anchor="w",
                font=("Microsoft YaHei UI", 13),
                fg_color="transparent",
                text_color=("gray20", "gray80"),
                hover_color=("gray85", "#333333"),
                command=lambda c=cat_id: self.switch_category(c)
            )
            btn.pack(side="left", fill="x", expand=True, padx=(5, 10))

            btn.indicator = indicator # Store ref
            self.category_buttons[cat_id] = btn

            # Add tooltip
            CTkToolTip(btn, tooltip, delay=300)

    def switch_category(self, category_name):
        """Switch the content area to the selected category"""
        if self.current_category == category_name:
            return

        # Update button styles
        for cat_id, btn in self.category_buttons.items():
            if cat_id == category_name:
                btn.configure(fg_color=("gray85", "#333333"), text_color=("#3B8ED0", "#3B8ED0"))
                btn.indicator.configure(fg_color="#3B8ED0")
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "gray80"))
                btn.indicator.configure(fg_color="transparent")

        self.current_category = category_name

        # Clear existing content
        for widget in self.settings_inner.winfo_children():
            widget.destroy()

        # Reset scroll
        self.settings_canvas.yview_moveto(0)

        # Build new content based on category
        parent = self.settings_inner

        if category_name == "stats":
            self.create_stats_card(parent)
            self.create_heatmap_card(parent)
            self.create_data_card(parent)
            self.create_cache_card(parent)

        elif category_name == "general":
            self.create_behavior_card(parent)
            self.create_hotkey_card(parent)

        elif category_name == "dicts":
            self.create_dict_sources_card(parent)
            self.create_appearance_card(parent)

        elif category_name == "about":
            self.create_about_card(parent)
            self.create_donate_card(parent)

        # Force refresh needed for some widgets (like heatmap)
        self.after(50, self.refresh_settings)

    def get_canvas_bg(self):
        # Helper to get bg color based on theme
        mode = ctk.get_appearance_mode()
        return "#2b2b2b" if mode == "Dark" else "gray95"

    def on_canvas_configure(self, event):
        self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox("all"))
        self.settings_canvas.itemconfig(self.settings_canvas_window, width=event.width)

    def on_mousewheel(self, event):
        self.settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def create_section_header(self, parent, icon, title, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=(20, 15))
        icon_bg = ctk.CTkFrame(frame, width=36, height=36, corner_radius=8, fg_color=color)
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=icon, font=("Segoe UI Emoji", 20), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(frame, text=title, font=("Microsoft YaHei UI", 16, "bold")).pack(side="left", padx=12)

    def create_stats_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=(10, 8))
        self.create_section_header(card, "📊", "学习统计", "#3B8ED0")

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=(0, 8))

        total_box = ctk.CTkFrame(row1, fg_color=("#e3f2fd", "#1a237e"), corner_radius=10)
        total_box.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(total_box, text="📚 总单词", font=("Microsoft YaHei UI", 12), text_color="gray").pack(pady=(10, 2))
        self.lbl_total_words = ctk.CTkLabel(total_box, text="0", font=("Microsoft YaHei UI", 24, "bold"))
        self.lbl_total_words.pack(pady=(0, 10))

        mastered_box = ctk.CTkFrame(row1, fg_color=("#e8f5e9", "#1b5e20"), corner_radius=10)
        mastered_box.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(mastered_box, text="🏆 已掌握", font=("Microsoft YaHei UI", 12), text_color="gray").pack(pady=(10, 2))
        self.lbl_mastered = ctk.CTkLabel(mastered_box, text="0 (0%)", font=("Microsoft YaHei UI", 24, "bold"))
        self.lbl_mastered.pack(pady=(0, 10))

        due_box = ctk.CTkFrame(card, fg_color=("#fff3e0", "#e65100"), corner_radius=10)
        due_box.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(due_box, text="⏰ 今日待复习", font=("Microsoft YaHei UI", 12), text_color="gray").pack(pady=(10, 2))
        self.lbl_due_today = ctk.CTkLabel(due_box, text="0 个", font=("Microsoft YaHei UI", 24, "bold"))
        self.lbl_due_today.pack(pady=(0, 10))

        # Total Study Time (Added)
        time_box = ctk.CTkFrame(card, fg_color=("#f3e5f5", "#4a148c"), corner_radius=10)
        time_box.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(time_box, text="⏱️ 累计学习时长", font=("Microsoft YaHei UI", 12), text_color="gray").pack(pady=(10, 2))
        self.lbl_total_time = ctk.CTkLabel(time_box, text="0 分钟", font=("Microsoft YaHei UI", 24, "bold"))
        self.lbl_total_time.pack(pady=(0, 10))

    def create_heatmap_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "🔥", "学习热力图 (过去一年)", "#FF9800")

        heatmap_container = ctk.CTkFrame(card, fg_color="transparent")
        heatmap_container.pack(fill="x", padx=20, pady=(0, 20))

        self.heatmap_canvas = tk.Canvas(
            heatmap_container, height=95,
            bg=self.get_canvas_bg().replace("gray95", "white"), # slight adjust
            highlightthickness=0, bd=0
        )
        self.heatmap_canvas.pack(fill="x", expand=True)

    def create_dict_sources_card(self, parent):
        """创建多词典源配置卡片"""
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "📚", "词典源设置", "#673AB7")

        # 说明文字
        ctk.CTkLabel(
            card,
            text="在单词详情页查询多个词典，获取更全面的释义",
            font=("Microsoft YaHei UI", 12),
            text_color=("gray40", "gray60"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 10))

        # 词典开关容器
        dict_frame = ctk.CTkFrame(card, fg_color=("gray95", "#1e1e1e"), corner_radius=10)
        dict_frame.pack(fill="x", padx=20, pady=(0, 15))

        # 词典配置
        dict_configs = [
            ("youdao", "📗 有道词典", "中文释义准确，词根词缀丰富", True),
            ("cambridge", "🏰 Cambridge Dictionary", "权威英英释义，高质量例句", True),
            ("bing", "🔷 Bing 词典", "词形变化、常用搭配", True),
            ("freedict", "📖 Free Dictionary", "英英释义，深度理解词义", True),
        ]

        self.dict_switches = {}

        for dict_id, name, desc, default in dict_configs:
            row = ctk.CTkFrame(dict_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=10)

            # 左侧：名称和描述
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                left,
                text=name,
                font=("Microsoft YaHei UI", 13, "bold"),
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=desc,
                font=("Microsoft YaHei UI", 11),
                text_color=("gray50", "gray60"),
                anchor="w"
            ).pack(anchor="w")

            # 右侧：开关
            switch = ctk.CTkSwitch(
                row,
                text="",
                width=50,
                command=lambda d=dict_id: self.on_dict_switch_change(d)
            )
            switch.pack(side="right", padx=10)

            # 有道词典固定开启（作为主词典）
            if dict_id == "youdao":
                switch.select()
                switch.configure(state="disabled")

            self.dict_switches[dict_id] = switch

        # 分隔线
        ctk.CTkFrame(card, height=1, fg_color=("gray80", "gray40")).pack(fill="x", padx=20, pady=5)

        # 提示
        ctk.CTkLabel(
            card,
            text="💡 有道词典为主词典，用于保存单词到词库，不可关闭",
            font=("Microsoft YaHei UI", 11),
            text_color=("gray50", "gray60"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(5, 15))

    def on_dict_switch_change(self, dict_id):
        """词典开关变化"""
        if dict_id not in self.dict_switches:
            return

        switch = self.dict_switches[dict_id]
        is_enabled = switch.get() == 1

        # 获取或初始化词典配置
        if "dict_sources" not in self.controller.config:
            from ..config import get_default_config
            default_cfg = get_default_config()
            self.controller.config["dict_sources"] = default_cfg["dict_sources"]

        self.controller.config["dict_sources"][dict_id] = is_enabled
        save_config(self.controller.config)

    def create_hotkey_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "⌨️", "快捷键设置", "#607D8B")

        ctk.CTkLabel(card, text="全局唤醒快捷键", font=("Microsoft YaHei UI", 13), anchor="w").pack(fill="x", padx=20, pady=(0, 8))
        hk_input_row = ctk.CTkFrame(card, fg_color="transparent")
        hk_input_row.pack(fill="x", padx=20, pady=(0, 15))

        self.entry_hk = ctk.CTkEntry(hk_input_row, height=40, font=("Microsoft YaHei UI", 14), placeholder_text="例如: ctrl+alt+v")
        self.entry_hk.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(hk_input_row, text="💾 保存", height=40, width=100, font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#4CAF50", hover_color="#45a049", command=self.update_hotkey).pack(side="left")

        # Auto-copy on hotkey toggle
        auto_copy_row = ctk.CTkFrame(card, fg_color="transparent")
        auto_copy_row.pack(fill="x", padx=20, pady=(0, 15))

        auto_copy_left = ctk.CTkFrame(auto_copy_row, fg_color="transparent")
        auto_copy_left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            auto_copy_left,
            text="唤醒时自动复制选中文字",
            font=("Microsoft YaHei UI", 13),
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            auto_copy_left,
            text="按下快捷键时自动发送 Ctrl+C 复制选中内容",
            font=("Microsoft YaHei UI", 11),
            text_color=("gray50", "gray60"),
            anchor="w"
        ).pack(anchor="w")

        self.auto_copy_switch = ctk.CTkSwitch(
            auto_copy_row,
            text="",
            width=50,
            command=self.on_auto_copy_change
        )
        self.auto_copy_switch.pack(side="right", padx=10)

        # App Shortcuts Display
        ctk.CTkLabel(card, text="应用内快捷键 (固定)", font=("Microsoft YaHei UI", 13, "bold"), anchor="w").pack(fill="x", padx=20, pady=(10, 8))

        shortcuts = [
            ("Ctrl + N", "🏠 词汇中心 (Vocab Center)"),
            ("Ctrl + L", "📚 单词列表 (List Page)"),
            ("Ctrl + R", "🧠 智能复习 (Review Page)"),
            ("Ctrl + S", "⚙️ 设置 (Settings Page)")
        ]

        sc_frame = ctk.CTkFrame(card, fg_color="transparent")
        sc_frame.pack(fill="x", padx=20, pady=(0, 20))

        for keys, desc in shortcuts:
            row = ctk.CTkFrame(sc_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=keys, font=("Consolas", 12, "bold"), width=80, anchor="w", text_color="#3B8ED0").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Microsoft YaHei UI", 12), anchor="w", text_color="gray").pack(side="left")

    def create_cache_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "🗂️", "缓存管理", "#FFC107")

        cache_info_box = ctk.CTkFrame(card, fg_color=("#f5f5f5", "#1e1e1e"), corner_radius=10)
        cache_info_box.pack(fill="x", padx=20, pady=(0, 10))

        # 音频缓存行
        audio_cache_row = ctk.CTkFrame(cache_info_box, fg_color="transparent")
        audio_cache_row.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(audio_cache_row, text="🎵 音频缓存", font=("Microsoft YaHei UI", 13)).pack(side="left")
        self.lbl_cache = ctk.CTkLabel(audio_cache_row, text="计算中...", font=("Microsoft YaHei UI", 13, "bold"))
        self.lbl_cache.pack(side="left", padx=10)

        # 词典缓存行
        dict_cache_row = ctk.CTkFrame(cache_info_box, fg_color="transparent")
        dict_cache_row.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(dict_cache_row, text="📚 词典缓存", font=("Microsoft YaHei UI", 13)).pack(side="left")
        self.lbl_dict_cache = ctk.CTkLabel(dict_cache_row, text="计算中...", font=("Microsoft YaHei UI", 13, "bold"))
        self.lbl_dict_cache.pack(side="left", padx=10)

        # 清理按钮行
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(btn_row, text="🗑️ 清理音频", height=40, font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#f44336", hover_color="#da190b", command=self.clear_cache).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(btn_row, text="🗑️ 清理词典", height=40, font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#FF9800", hover_color="#F57C00", command=self.clear_dict_cache).pack(side="left", fill="x", expand=True, padx=(5, 0))

    def create_appearance_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "🎨", "外观设置", "#9C27B0")

        theme_row = ctk.CTkFrame(card, fg_color="transparent")
        theme_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(theme_row, text="主题模式", font=("Microsoft YaHei UI", 13)).pack(side="left")
        self.theme_dropdown = ctk.CTkOptionMenu(
            theme_row, values=["浅色", "深色", "跟随系统"], width=120, height=35,
            font=("Microsoft YaHei UI", 13), command=self.change_theme
        )
        self.theme_dropdown.pack(side="right")

    def create_behavior_card(self, parent):
        """创建系统行为设置卡片"""
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "⚙️", "系统行为", "#795548")

        # 关闭行为设置
        close_row = ctk.CTkFrame(card, fg_color="transparent")
        close_row.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            close_row,
            text="关闭窗口时",
            font=("Microsoft YaHei UI", 13)
        ).pack(side="left")

        self.close_action_var = ctk.StringVar(value="ask")
        self.close_dropdown = ctk.CTkOptionMenu(
            close_row,
            values=["每次询问", "最小化到托盘", "直接退出"],
            width=140,
            height=35,
            font=("Microsoft YaHei UI", 13),
            command=self.on_close_action_change
        )
        self.close_dropdown.pack(side="right")

        # 提醒设置
        reminder_row = ctk.CTkFrame(card, fg_color="transparent")
        reminder_row.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            reminder_row,
            text="复习提醒间隔",
            font=("Microsoft YaHei UI", 13)
        ).pack(side="left")

        self.reminder_dropdown = ctk.CTkOptionMenu(
            reminder_row,
            values=["15 分钟", "30 分钟", "1 小时", "2 小时", "关闭提醒"],
            width=140,
            height=35,
            font=("Microsoft YaHei UI", 13),
            command=self.on_reminder_change
        )
        self.reminder_dropdown.pack(side="right")

        # 说明文字
        ctk.CTkLabel(
            card,
            text="提示：关闭窗口时选择\"每次询问\"可在关闭时选择行为，并可勾选记住选择",
            font=("Microsoft YaHei UI", 11),
            text_color="gray",
            wraplength=500,
            anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 20))

    def on_close_action_change(self, choice):
        """关闭行为改变"""
        action_map = {
            "每次询问": "ask",
            "最小化到托盘": "minimize",
            "直接退出": "exit"
        }
        action = action_map.get(choice, "ask")
        self.controller.config["close_action"] = action
        save_config(self.controller.config)

    def on_reminder_change(self, choice):
        """提醒间隔改变"""
        interval_map = {
            "15 分钟": 15,
            "30 分钟": 30,
            "1 小时": 60,
            "2 小时": 120,
            "关闭提醒": 0
        }
        interval = interval_map.get(choice, 30)
        self.controller.config["reminder_interval"] = interval
        save_config(self.controller.config)

        # 更新调度器间隔
        if hasattr(self.controller, 'review_scheduler'):
            if interval == 0:
                self.controller.review_scheduler.stop()
            else:
                self.controller.review_scheduler.check_interval = interval * 60
                if not self.controller.review_scheduler.running:
                    self.controller.review_scheduler.start()

    def on_auto_copy_change(self):
        """自动复制开关改变"""
        is_enabled = self.auto_copy_switch.get() == 1
        self.controller.config["auto_copy_on_hotkey"] = is_enabled
        save_config(self.controller.config)

    def create_donate_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "❤️", "支持开发", "#E91E63")

        ctk.CTkLabel(card, text="如果这个应用对您有帮助，欢迎支持作者继续开发 💖",
                    font=("Microsoft YaHei UI", 13), text_color=("gray40", "gray60"), anchor="w").pack(fill="x", padx=20, pady=(0, 15))

        self.btn_donate = ctk.CTkButton(
            card, text="☕ 请我喝杯咖啡", height=50, font=("Microsoft YaHei UI", 16, "bold"),
            fg_color=("#E67E22", "#D35400"), hover_color=("#E67E22", "#D35400"), corner_radius=12,
            command=self.toggle_donate_qr
        )
        self.btn_donate.pack(fill="x", padx=20, pady=(0, 10))

        self.qr_container = ctk.CTkFrame(card, fg_color=("#f0f0f0", "#1e1e1e"), corner_radius=10)
        self.donate_qr_loaded = False
        self.donate_qr_available = os.path.exists(os.path.join(RESOURCE_DIR, "donate_qr.png"))
        self.qr_visible = False

    def create_data_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=8)
        self.create_section_header(card, "💾", "数据管理", "#607D8B")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(row, text="📤 导出 CSV", height=40, font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#3B8ED0", command=self.export_data).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(row, text="📥 导入 CSV", height=40, font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#3B8ED0", command=self.import_data).pack(side="left", fill="x", expand=True, padx=(5, 0))

    def export_data(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filename:
            words = self.controller.db.get_all_words()
            success, msg = ExportService.export_to_csv(filename, words)
            if success:
                messagebox.showinfo("成功", msg)
            else:
                messagebox.showerror("失败", msg)

    def import_data(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if filename:
            if messagebox.askyesno("确认", "导入将合并现有数据，重复单词将更新释义。\n确定继续吗？"):
                success, msg = ExportService.import_from_csv(filename, self.controller.db)
                if success:
                    messagebox.showinfo("成功", msg)
                    self.controller.reload_vocab_list()
                    self.refresh_settings()
                else:
                    messagebox.showerror("失败", msg)

    def create_about_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=15)
        card.pack(fill="x", padx=15, pady=(8, 15))
        self.create_section_header(card, "ℹ️", "关于", "#2196F3")
        ctk.CTkLabel(card, text=f"智能生词本 v{APP_VERSION}", font=("Microsoft YaHei UI", 16, "bold"), anchor="w").pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="基于间隔重复算法的智能单词记忆工具", font=("Microsoft YaHei UI", 12), text_color=("gray40", "gray60"), anchor="w").pack(fill="x", padx=20, pady=2)

        # Check Update Section
        update_row = ctk.CTkFrame(card, fg_color="transparent")
        update_row.pack(fill="x", padx=20, pady=(10, 15))

        self.btn_check_update = ctk.CTkButton(
            update_row,
            text="🔄 检查更新",
            height=32,
            width=120,
            font=("Microsoft YaHei UI", 13),
            command=self.check_for_updates
        )
        self.btn_check_update.pack(side="left")

        self.lbl_update_status = ctk.CTkLabel(update_row, text="", font=("Microsoft YaHei UI", 12), text_color="gray")
        self.lbl_update_status.pack(side="left", padx=10)

    def check_for_updates(self):
        self.btn_check_update.configure(state="disabled", text="Checking...")
        self.lbl_update_status.configure(text="")
        UpdateService.check_for_updates(self.on_update_checked)

    def on_update_checked(self, has_update, info):
        self.btn_check_update.configure(state="normal", text="🔄 检查更新")

        if has_update and info:
            version = info.get("version", "Unknown")
            changelog = info.get("changelog", "No details")
            download_url = info.get("download_url")

            msg = f"发现新版本 v{version}!\n\n更新内容:\n{changelog}\n\n是否立即更新？"
            if messagebox.askyesno("版本更新", msg):
                self.start_download(download_url)
        else:
            self.lbl_update_status.configure(text="当前已是最新版本")
            # Clear status after 3 seconds
            self.after(3000, lambda: self.lbl_update_status.configure(text=""))

    def start_download(self, url):
        if not url:
            messagebox.showerror("错误", "无效的下载链接")
            return

        self.btn_check_update.configure(state="disabled", text="Downloading...")
        self.lbl_update_status.configure(text="正在下载更新...")

        # Create a progress window
        self.progress_window = ctk.CTkToplevel(self)
        self.progress_window.title("下载更新")
        self.progress_window.geometry("300x150")
        self.progress_window.attributes("-topmost", True)
        self.progress_window.grab_set()

        ctk.CTkLabel(self.progress_window, text="正在下载更新...", font=("Microsoft YaHei UI", 14)).pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.progress_window, width=200)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(self.progress_window, text="0%")
        self.lbl_progress.pack(pady=5)

        UpdateService.download_update(url, self.on_download_progress, self.on_download_complete)

    def on_download_progress(self, progress):
        if progress == -1:
            self.progress_window.destroy()
            messagebox.showerror("错误", "下载失败")
            self.btn_check_update.configure(state="normal", text="🔄 检查更新")
            self.lbl_update_status.configure(text="下载失败")
            return

        self.progress_bar.set(progress / 100)
        self.lbl_progress.configure(text=f"{int(progress)}%")

    def on_download_complete(self, file_path):
        self.progress_window.destroy()
        self.btn_check_update.configure(state="normal", text="🔄 检查更新")
        self.lbl_update_status.configure(text="下载完成")

        if messagebox.askyesno("下载完成", "更新已下载，是否立即重启应用？"):
            UpdateService.restart_and_update(file_path)

    def on_show(self):
        self.refresh_settings()

    def refresh_settings(self):
        # Update Stats (if visible)
        if hasattr(self, 'lbl_total_words') and self.lbl_total_words.winfo_exists():
            stats = self.controller.db.get_statistics()
            total = stats['total']
            mastered = stats['mastered']
            due_today = stats['due_today']

            self.lbl_total_words.configure(text=f"{total}")
            percentage = mastered*100//total if total > 0 else 0
            self.lbl_mastered.configure(text=f"{mastered} ({percentage}%)")
            self.lbl_due_today.configure(text=f"{due_today} 个")

            # Update Total Study Time
            total_seconds = self.controller.db.get_total_study_time()
            if total_seconds < 60:
                time_str = f"{total_seconds} 秒"
            elif total_seconds < 3600:
                time_str = f"{total_seconds // 60} 分钟"
            else:
                hours = total_seconds // 3600
                mins = (total_seconds % 3600) // 60
                time_str = f"{hours} 小时 {mins} 分钟"
            self.lbl_total_time.configure(text=time_str)

            self.draw_heatmap()

        # Update Hotkey (if visible)
        if hasattr(self, 'entry_hk') and self.entry_hk.winfo_exists():
            self.entry_hk.delete(0, "end")
            self.entry_hk.insert(0, self.controller.current_hotkey)

        # Update Auto-copy switch (if visible)
        if hasattr(self, 'auto_copy_switch') and self.auto_copy_switch.winfo_exists():
            auto_copy = self.controller.config.get("auto_copy_on_hotkey", True)
            if auto_copy:
                self.auto_copy_switch.select()
            else:
                self.auto_copy_switch.deselect()

        # Update Theme (if visible)
        if hasattr(self, 'theme_dropdown') and self.theme_dropdown.winfo_exists():
            current_mode = ctk.get_appearance_mode()
            mode_map = {"Light": "浅色", "Dark": "深色", "System": "跟随系统"}
            self.theme_dropdown.set(mode_map.get(current_mode, "浅色"))

        # Update Close Action (if visible)
        if hasattr(self, 'close_dropdown') and self.close_dropdown.winfo_exists():
            close_action = self.controller.config.get("close_action", "ask")
            close_action_display = {
                "ask": "每次询问",
                "minimize": "最小化到托盘",
                "exit": "直接退出"
            }
            self.close_dropdown.set(close_action_display.get(close_action, "每次询问"))

        # Update Reminder (if visible)
        if hasattr(self, 'reminder_dropdown') and self.reminder_dropdown.winfo_exists():
            reminder_interval = self.controller.config.get("reminder_interval", 30)
            interval_display = {
                15: "15 分钟",
                30: "30 分钟",
                60: "1 小时",
                120: "2 小时",
                0: "关闭提醒"
            }
            self.reminder_dropdown.set(interval_display.get(reminder_interval, "30 分钟"))

        # Update Dict Sources (if visible)
        if hasattr(self, 'dict_switches'):
            from ..config import get_default_config
            default_cfg = get_default_config()
            dict_sources = self.controller.config.get("dict_sources", default_cfg["dict_sources"])
            for dict_id, switch in self.dict_switches.items():
                if switch.winfo_exists():
                    if dict_id == "youdao":
                        continue  # 有道词典始终开启
                    is_enabled = dict_sources.get(dict_id, True)
                    if is_enabled:
                        switch.select()
                    else:
                        switch.deselect()

        # Update Cache Info (if visible)
        if hasattr(self, 'lbl_cache') and self.lbl_cache.winfo_exists():
            size = 0
            count = 0
            if os.path.exists(SOUNDS_DIR):
                for f in os.listdir(SOUNDS_DIR):
                    fp = os.path.join(SOUNDS_DIR, f)
                    if os.path.isfile(fp):
                        size += os.path.getsize(fp)
                        count += 1
            self.lbl_cache.configure(text=f"{count} 个文件 ({size/1024/1024:.1f} MB)")

        # Update Dict Cache Info (if visible)
        if hasattr(self, 'lbl_dict_cache') and self.lbl_dict_cache.winfo_exists():
            try:
                stats = self.controller.db.get_dict_cache_stats()
                total = stats.get('total', 0)
                self.lbl_dict_cache.configure(text=f"{total} 条记录")
            except Exception:
                self.lbl_dict_cache.configure(text="0 条记录")

    def update_hotkey(self):
        if not hasattr(self, 'entry_hk') or not self.entry_hk.winfo_exists():
            return

        new_hk = self.entry_hk.get().strip()
        if new_hk:
            self.controller.current_hotkey = new_hk
            self.controller.config['hotkey'] = new_hk
            save_config(self.controller.config)
            self.controller.setup_hotkey()
            messagebox.showinfo("成功", f"快捷键已更新为: {new_hk}")

    def clear_cache(self):
        if messagebox.askyesno("确认", "确定清空所有下载的音频文件吗？"):
            if os.path.exists(SOUNDS_DIR):
                try:
                    shutil.rmtree(SOUNDS_DIR)
                    os.makedirs(SOUNDS_DIR)
                except Exception as e:
                    messagebox.showerror("错误", f"清理失败: {e}")
            self.refresh_settings()
            messagebox.showinfo("完成", "音频缓存已清理")

    def clear_dict_cache(self):
        """清理词典查询缓存"""
        if messagebox.askyesno("确认", "确定清空所有词典查询缓存吗？\n\n清理后再次查询单词时需要重新从网络获取。"):
            try:
                deleted = self.controller.db.clear_all_dict_cache()
                self.refresh_settings()
                messagebox.showinfo("完成", f"已清理 {deleted} 条词典缓存")
            except Exception as e:
                messagebox.showerror("错误", f"清理失败: {e}")

    def change_theme(self, choice):
        theme_map = {"浅色": "Light", "深色": "Dark", "跟随系统": "System"}
        mode = theme_map.get(choice, "Light")
        ctk.set_appearance_mode(mode)
        self.controller.config['theme'] = mode
        save_config(self.controller.config)

        self.settings_canvas.configure(bg=self.get_canvas_bg())
        if hasattr(self, 'heatmap_canvas') and self.heatmap_canvas.winfo_exists():
             bg = self.get_canvas_bg().replace("gray95", "white")
             self.heatmap_canvas.configure(bg=bg)
             self.after(100, self.draw_heatmap)

    def draw_heatmap(self):
        if not hasattr(self, 'heatmap_canvas') or not self.heatmap_canvas.winfo_exists():
            return

        self.heatmap_canvas.delete("all")
        data = self.controller.db.get_review_heatmap_data()

        # Get scaling factor from CustomTkinter
        try:
            scaling = self._get_widget_scaling()
        except AttributeError:
            scaling = 1.0

        # Apply scaling to fixed sizes
        box_size = 8 * scaling
        gap = 1 * scaling
        margin_left = 40 * scaling
        margin_top = 25 * scaling
        font_size = int(7 * scaling)

        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"

        # Ensure canvas bg is correct
        bg = "#2b2b2b" if is_dark else "white"
        
        # Calculate required height dynamically
        required_height = margin_top + 7 * (box_size + gap) + (10 * scaling)
        self.heatmap_canvas.configure(bg=bg, height=required_height)

        if is_dark:
            colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
            text_color = "gray60"
        else:
            colors = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
            text_color = "gray50"

        today = datetime.now()
        end_date = today
        start_date = end_date - timedelta(days=364)
        current_weekday = start_date.weekday()
        days_to_subtract = (current_weekday + 1) % 7
        start_date -= timedelta(days=days_to_subtract)

        current = start_date
        col = 0
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            count = data.get(date_str, 0)

            if count == 0: color = colors[0]
            elif count <= 3: color = colors[1]
            elif count <= 6: color = colors[2]
            elif count <= 9: color = colors[3]
            else: color = colors[4]

            day_of_week = (current.weekday() + 1) % 7
            x1 = margin_left + col * (box_size + gap)
            y1 = margin_top + day_of_week * (box_size + gap)

            self.heatmap_canvas.create_rectangle(x1, y1, x1+box_size, y1+box_size, fill=color, outline="")

            if day_of_week == 0 and current.day <= 7:
                 self.heatmap_canvas.create_text(x1, margin_top - (10 * scaling), text=months[current.month-1],
                                                fill=text_color, font=("Arial", font_size), anchor="w")

            current += timedelta(days=1)
            if day_of_week == 6:
                col += 1

        days_label = ["Mon", "Wed", "Fri"]
        days_idx = [1, 3, 5]
        for i, label in zip(days_idx, days_label):
            y = margin_top + i * (box_size + gap) + box_size/2
            self.heatmap_canvas.create_text(margin_left - (5 * scaling), y, text=label, fill=text_color, font=("Arial", font_size), anchor="e")

    def toggle_donate_qr(self):
        if not self.donate_qr_available:
            messagebox.showinfo("提示", "二维码图片未找到")
            return

        if not self.donate_qr_loaded:
            try:
                img_path = os.path.join(RESOURCE_DIR, "donate_qr.png")
                original_img = Image.open(img_path)
                img_width, img_height = original_img.size
                max_size = 300
                if img_width > max_size or img_height > max_size:
                    ratio = min(max_size / img_width, max_size / img_height)
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                else:
                    new_width, new_height = img_width, img_height

                self.donate_img = ctk.CTkImage(light_image=original_img, dark_image=original_img, size=(new_width, new_height))
                self.lbl_qr = ctk.CTkLabel(self.qr_container, image=self.donate_img, text="")
                self.lbl_qr.pack(padx=20, pady=(20, 10))
                ctk.CTkLabel(self.qr_container, text="扫码支持作者 💖", font=("Microsoft YaHei UI", 13, "bold"), text_color=("#4CAF50", "#66BB6A")).pack(pady=(0, 20))
                self.donate_qr_loaded = True
            except Exception as e:
                ctk.CTkLabel(self.qr_container, text=f"加载失败: {str(e)}", font=("Microsoft YaHei UI", 11), text_color="gray").pack(padx=40, pady=40)
                self.donate_qr_available = False
                return

        if self.qr_visible:
            self.qr_container.pack_forget()
            self.btn_donate.configure(text="☕ 请我喝杯咖啡")
            self.qr_visible = False
        else:
            self.qr_container.pack(fill="x", pady=(0, 10))
            self.btn_donate.configure(text="❌ 收起二维码")
            self.qr_visible = True
