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
        
        # Hide tooltip when window is minimized/hidden
        root = self.widget.winfo_toplevel()
        root.bind("<Unmap>", self._on_window_hide, add="+")

        self.tooltip = None
        self.id = None
        self.x = self.y = 0

    def _on_enter(self, event=None):
        self.id = self.widget.after(self.delay, self._show_tooltip)

    def _on_leave(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        self._hide_tooltip()

    def _on_motion(self, event=None):
        self.x = event.x_root
        self.y = event.y_root
        if self.tooltip:
            self._position_tooltip()

    def _show_tooltip(self):
        if self.tooltip:
            return

        root = self.widget.winfo_toplevel()
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        # Make tooltip follow the main window (hide when minimized)
        self.tooltip.transient(root)

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

    def _hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def _position_tooltip(self):
        if self.tooltip:
            x = self.x + 15
            y = self.y + 15
            self.tooltip.geometry(f"+{x}+{y}")

    def _on_window_hide(self, event=None):
        """Hide tooltip when window is minimized"""
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
