import tkinter as tk
import customtkinter as ctk
import threading
import re
from ..services.audio_service import AudioService


class CTkToolTip:
    """Elegant tooltip for CTk widgets"""

    def __init__(self, widget, message, delay=500, **kwargs):
        self.widget = widget
        self.message = message
        self.delay = delay
        self.options = {
            "bg": ("gray95", "#2b2b2b"),
            "fg": ("gray20", "gray80"),
            "corner_radius": 6,
            "font": ("Microsoft YaHei UI", 11),
            "padding": (10, 6),
        }
        self.options.update(kwargs)

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<Motion>", self._on_motion, add="+")
        # 绑定 Button-1 点击事件，点击时隐藏 tooltip
        self.widget.bind("<Button-1>", self._on_click, add="+")

        # Hide tooltip when window is minimized/hidden/loses focus
        root = self.widget.winfo_toplevel()
        root.bind("<Unmap>", self._on_window_hide, add="+")
        root.bind("<FocusOut>", self._on_window_hide, add="+")

        # 绑定 widget 的 Destroy 事件
        self.widget.bind("<Destroy>", self._on_widget_destroy, add="+")

        self.tooltip = None
        self.id = None
        self.x = self.y = 0
        self._entered = False
        self._visible = False
        self._check_id = None
        self._destroyed = False

    def _on_enter(self, event=None):
        if self._destroyed:
            return
        self._entered = True
        if event:
            self.x = event.x_root
            self.y = event.y_root
        self._cancel_scheduled_show()
        self.id = self.widget.after(self.delay, self._show_tooltip)

    def _on_motion(self, event=None):
        """Update position when mouse moves over widget"""
        if event:
            self.x = event.x_root
            self.y = event.y_root

    def _on_leave(self, event=None):
        self._entered = False
        self._cancel_scheduled_show()
        self._cancel_check()
        self._hide_tooltip()

    def _on_click(self, event=None):
        """点击时隐藏 tooltip"""
        self._entered = False
        self._cancel_scheduled_show()
        self._cancel_check()
        self._hide_tooltip()

    def _on_widget_destroy(self, event=None):
        """widget 被销毁时清理"""
        self._destroyed = True
        self._cancel_scheduled_show()
        self._cancel_check()
        self._hide_tooltip()

    def _cancel_scheduled_show(self):
        """取消已调度的显示"""
        if self.id:
            try:
                self.widget.after_cancel(self.id)
            except Exception:
                pass
            self.id = None

    def _cancel_check(self):
        """取消定时检查"""
        if self._check_id:
            try:
                self.widget.after_cancel(self._check_id)
            except Exception:
                pass
            self._check_id = None

    def _show_tooltip(self):
        self.id = None  # 已执行，清除引用

        # Check if mouse is still over widget before showing
        if not self._entered or self._destroyed:
            return

        if self.tooltip:
            return

        # 再次检查 widget 是否存在
        try:
            if not self.widget.winfo_exists():
                return
        except Exception:
            return

        self._visible = True
        try:
            root = self.widget.winfo_toplevel()
            self.tooltip = ctk.CTkToplevel(self.widget)
            self.tooltip.overrideredirect(True)
            self.tooltip.attributes("-topmost", True)
            self.tooltip.transient(root)
            # 禁用 tooltip 窗口接收焦点和鼠标事件
            self.tooltip.attributes("-disabled", True)

            # Get colors based on theme
            mode = ctk.get_appearance_mode()
            bg = self.options["bg"][1] if mode == "Dark" else self.options["bg"][0]
            fg = self.options["fg"][1] if mode == "Dark" else self.options["fg"][0]

            self.tooltip.configure(fg_color=bg)
            self.tooltip._border_color = ("gray75", "#3a3a3a")
            self.tooltip._border_width = 1

            frame = ctk.CTkFrame(self.tooltip, fg_color="transparent", corner_radius=self.options["corner_radius"])
            frame.pack(fill="both", expand=True, padx=self.options["padding"][0], pady=self.options["padding"][1])

            ctk.CTkLabel(
                frame,
                text=self.message,
                font=self.options["font"],
                text_color=fg,
                wraplength=300
            ).pack()

            self._position_tooltip()

            # 启动定时检查，确保 tooltip 在鼠标离开后隐藏
            self._start_check()
        except Exception:
            self._hide_tooltip()

    def _start_check(self):
        """定时检查鼠标是否仍在 widget 上"""
        self._cancel_check()
        if not self._destroyed:
            try:
                # 使用更短的检查间隔 (100ms) 提高响应速度
                self._check_id = self.widget.after(100, self._check_mouse_position)
            except Exception:
                pass

    def _check_mouse_position(self):
        """检查鼠标位置，如果不在 widget 上则隐藏 tooltip"""
        self._check_id = None  # 已执行，清除引用

        if not self.tooltip or self._destroyed:
            return

        try:
            # 检查 widget 是否存在且可见
            if not self.widget.winfo_exists():
                self._hide_tooltip()
                return

            # 检查 widget 是否被映射（可见）
            if not self.widget.winfo_ismapped():
                self._hide_tooltip()
                return

            wx = self.widget.winfo_rootx()
            wy = self.widget.winfo_rooty()
            ww = self.widget.winfo_width()
            wh = self.widget.winfo_height()

            # 获取当前鼠标位置
            mx = self.widget.winfo_pointerx()
            my = self.widget.winfo_pointery()

            # 检查鼠标是否在 widget 范围内 (使用严格边界，不包含边缘)
            if not (wx < mx < wx + ww and wy < my < wy + wh):
                self._hide_tooltip()
                return

            # 继续检查
            self._start_check()
        except Exception:
            self._hide_tooltip()

    def _hide_tooltip(self):
        self._visible = False
        self._entered = False
        self._cancel_check()

        if self.tooltip:
            try:
                tooltip = self.tooltip
                self.tooltip = None  # Set to None FIRST to prevent race conditions
                tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None  # 确保置空

    def _position_tooltip(self):
        if self.tooltip:
            try:
                x = self.x + 15
                y = self.y + 15
                self.tooltip.geometry(f"+{x}+{y}")
            except Exception:
                pass

    def _on_window_hide(self, event=None):
        """Hide tooltip when window is minimized or loses focus"""
        self._hide_tooltip()
        return None  # Important: return None to let the event propagate

class BaseView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        """Override this to build the UI"""
        pass

    def on_show(self):
        """Called when the view is shown"""
        pass

    def play_audio(self, word, button=None):
        """Helper to play audio with button feedback"""
        if not AudioService.is_available():
            # Show toast or log?
            print("Audio not available")
            return

        # Clean the word before playing (remove punctuation)
        clean_word = self.clean_word(word) if hasattr(self, 'clean_word') else word.strip()
        if not clean_word:
            return

        def _play():
            if button:
                self.after(0, lambda: button.configure(text="⏳", fg_color="orange"))

            # Use a dummy callbacks or just call blocking
            # We can't easily use callbacks to update UI from thread without after
            # So we just run blocking and update UI after

            try:
                AudioService.play_word(clean_word)
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="green"))
            except Exception as e:
                print(f"Play error: {e}")
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="gray"))

        threading.Thread(target=_play, daemon=True).start()

    # ===== Context Menu Methods =====

    def create_context_menu(self):
        """Create the context menu for text widgets"""
        menu_font = ("Microsoft YaHei UI", 12)
        self.context_menu = tk.Menu(self, tearoff=0, font=menu_font)
        self.context_menu.add_command(label="复制 (Copy)", command=self.on_copy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="查词 (Look up)", command=self.on_lookup)
        self.current_text_widget = None

    def bind_context_menu(self, widget):
        """Bind right-click context menu to a widget"""
        widget.bind("<Button-3>", lambda e, w=widget: self.show_context_menu(e, w))
        widget.bind("<Button-2>", lambda e, w=widget: self.show_context_menu(e, w))  # macOS

    def show_context_menu(self, event, widget):
        """Show context menu if text is selected"""
        self.current_text_widget = widget
        if self.get_selected_text():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def get_selected_text(self):
        """Get selected text from current widget"""
        if not self.current_text_widget:
            return ""
        try:
            return self.current_text_widget.selection_get()
        except tk.TclError:
            return ""

    def clean_word(self, text):
        """Clean word by removing leading/trailing punctuation and extra whitespace.
        
        This fixes the issue where selecting text in context includes punctuation
        like 'word,' or 'word.' which causes audio download failures.
        """
        if not text:
            return ""
        # Strip whitespace first
        word = text.strip()
        # Remove leading and trailing punctuation (keep internal hyphens for compound words)
        word = re.sub(r'^[^\w]+|[^\w]+$', '', word, flags=re.UNICODE)
        return word

    def on_copy(self):
        """Copy selected text to clipboard"""
        text = self.get_selected_text()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()

    def on_lookup(self):
        """Override this in subclasses to implement lookup behavior"""
        pass
