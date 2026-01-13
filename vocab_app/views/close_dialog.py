"""
CloseDialog - 关闭行为选择对话框

仿照专业软件（QQ、微信等）的关闭确认对话框：
- 选择最小化到托盘或直接退出
- 可勾选"记住我的选择"
"""

import customtkinter as ctk
import tkinter as tk


class CloseDialog(ctk.CTkToplevel):
    """关闭行为选择对话框"""

    def __init__(self, master, on_result_callback):
        """
        Args:
            master: 父窗口
            on_result_callback: 结果回调 callback(action, remember)
                action: "minimize" | "exit" | "cancel"
                remember: bool - 是否记住选择
        """
        super().__init__(master)
        self.callback = on_result_callback
        self.result_action = "cancel"
        self.result_remember = False

        # 窗口设置
        self.title("关闭确认")
        self.geometry("400x380")
        self.resizable(False, False)

        # 居中显示
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 400) // 2
        y = master.winfo_y() + (master.winfo_height() - 380) // 2
        self.geometry(f"+{x}+{y}")

        # 模态
        self.transient(master)
        self.grab_set()

        self.setup_ui()

        # 关闭按钮行为
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def setup_ui(self):
        # 图标和标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 15))

        ctk.CTkLabel(
            header,
            text="📖",
            font=("Segoe UI Emoji", 36)
        ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(
            header,
            text="关闭程序时...",
            font=("Microsoft YaHei UI", 18, "bold")
        ).pack(side="left", anchor="w")

        # 选项区域
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=30, pady=10)

        self.choice_var = tk.StringVar(master=self, value="minimize")

        # 选项1：最小化到托盘
        option1_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        option1_frame.pack(fill="x", pady=5)

        self.radio_minimize = ctk.CTkRadioButton(
            option1_frame,
            text="最小化到系统托盘",
            variable=self.choice_var,
            value="minimize",
            font=("Microsoft YaHei UI", 14)
        )
        self.radio_minimize.pack(anchor="w")

        ctk.CTkLabel(
            option1_frame,
            text="程序将在后台运行，可从托盘恢复",
            font=("Microsoft YaHei UI", 11),
            text_color="gray"
        ).pack(anchor="w", padx=(24, 0))

        # 选项2：直接退出
        option2_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        option2_frame.pack(fill="x", pady=5)

        self.radio_exit = ctk.CTkRadioButton(
            option2_frame,
            text="直接退出程序",
            variable=self.choice_var,
            value="exit",
            font=("Microsoft YaHei UI", 14)
        )
        self.radio_exit.pack(anchor="w")

        ctk.CTkLabel(
            option2_frame,
            text="完全关闭程序，停止后台服务",
            font=("Microsoft YaHei UI", 11),
            text_color="gray"
        ).pack(anchor="w", padx=(24, 0))

        # 记住选择
        remember_frame = ctk.CTkFrame(self, fg_color="transparent")
        remember_frame.pack(fill="x", padx=30, pady=(15, 10))

        self.remember_var = tk.BooleanVar(master=self, value=False)
        self.checkbox_remember = ctk.CTkCheckBox(
            remember_frame,
            text="记住我的选择，下次不再询问",
            variable=self.remember_var,
            font=("Microsoft YaHei UI", 12),
            checkbox_width=20,
            checkbox_height=20
        )
        self.checkbox_remember.pack(anchor="w")

        # 按钮区域
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(10, 25))

        ctk.CTkButton(
            btn_frame,
            text="确定",
            width=100,
            height=36,
            font=("Microsoft YaHei UI", 13, "bold"),
            command=self.on_confirm
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            height=36,
            font=("Microsoft YaHei UI", 13),
            fg_color="gray",
            hover_color="gray30",
            command=self.on_cancel
        ).pack(side="right")

    def on_confirm(self):
        """确认选择"""
        self.result_action = self.choice_var.get()
        self.result_remember = self.remember_var.get()
        self.grab_release()
        self.destroy()
        if self.callback:
            self.callback(self.result_action, self.result_remember)

    def on_cancel(self):
        """取消"""
        self.result_action = "cancel"
        self.result_remember = False
        self.grab_release()
        self.destroy()
        if self.callback:
            self.callback("cancel", False)
