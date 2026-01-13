import customtkinter as ctk
import threading
from ..services.audio_service import AudioService

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

        def _play():
            if button:
                self.after(0, lambda: button.configure(text="⏳", fg_color="orange"))

            # Use a dummy callbacks or just call blocking
            # We can't easily use callbacks to update UI from thread without after
            # So we just run blocking and update UI after

            try:
                AudioService.play_word(word)
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="green"))
            except Exception as e:
                print(f"Play error: {e}")
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="gray"))

        threading.Thread(target=_play, daemon=True).start()
