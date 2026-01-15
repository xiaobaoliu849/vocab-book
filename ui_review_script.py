
import os
import sys
import customtkinter as ctk

# Ensure we can import the app modules
sys.path.append(os.getcwd())

from vocab_app.config import load_config, setup_theme
from vocab_app.views.list_view import ListView
from vocab_app.views.add_view import AddView
from vocab_app.views.detail_window import DetailWindow

def create_mock_controller():
    # Mock controller to provide necessary data and methods
    class MockController:
        def __init__(self):
            self.vocab_list = [
                {
                    'word': 'serendipity',
                    'phonetic': 'ˌserənˈdɪpəti',
                    'meaning': 'n. 意外发现珍奇事物的本领；机缘凑巧',
                    'tags': 'CET6, GRE',
                    'mastered': False,
                    'stage': 2,
                    'next_review_time': 0,
                    'example': 'The discovery of penicillin was a happy serendipity.'
                },
                {
                    'word': 'ephemeral',
                    'phonetic': 'əˈfemərəl',
                    'meaning': 'adj. 短暂的；朝生暮死的\nn. 短暂的事物',
                    'tags': 'TOEFL',
                    'mastered': True,
                    'stage': 5,
                    'next_review_time': 1234567890
                },
                {
                    'word': 'ubiquitous',
                    'phonetic': 'juːˈbɪkwɪtəs',
                    'meaning': 'adj. 无所不在的，普通的',
                    'mastered': False,
                    'stage': 0,
                    'next_review_time': 0
                }
            ] * 5  # Duplicate to fill list
            self.config = load_config()
            self.db = None # Mock DB if needed

        def reload_vocab_list(self):
            pass
            
    return MockController()

def capture_ui_mockup():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1000x700")
    root.title("UI Review Snapshot")

    controller = create_mock_controller()

    # Create a tabview to show multiple views
    tabview = ctk.CTkTabview(root)
    tabview.pack(fill="both", expand=True, padx=20, pady=20)

    # 1. List View
    tabview.add("List View")
    list_view = ListView(tabview.tab("List View"), controller)
    list_view.pack(fill="both", expand=True)
    list_view.on_show() # Trigger render

    # 2. Add View (Mocking appearance)
    tabview.add("Add View")
    add_view = AddView(tabview.tab("Add View"), controller)
    add_view.pack(fill="both", expand=True)

    # 3. Detail View (Separate Window)
    # We can't easily embed a Toplevel in a frame, but we can inspect the code visually
    # or just rely on the main views first.
    
    root.update()
    
    # Save screenshot (requires PIL)
    try:
        from PIL import ImageGrab
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        ImageGrab.grab(bbox=(x, y, x+w, y+h)).save("ui_snapshot.png")
        print("Snapshot saved to ui_snapshot.png")
    except ImportError:
        print("PIL not installed, cannot save screenshot. Please view the window.")

    # root.destroy() # Don't destroy immediately so we can see it if run interactively, 
    # but for automation we might want to close. 
    # For this task, I'll just rely on code analysis primarily as I can't see the screen directly unless I use the browser tool which is heavyweight.
    
    root.destroy() 

if __name__ == "__main__":
    capture_ui_mockup()
