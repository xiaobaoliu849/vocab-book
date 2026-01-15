
import customtkinter as ctk
from PIL import Image, ImageTk
import os

ctk.set_appearance_mode("System")

root = ctk.CTk()
root.geometry("400x300")
root.title("图标测试 Icon Test")

icon_path = "app.png"
print(f"Checking {icon_path}...")

if os.path.exists(icon_path):
    print(f"File exists! Size: {os.path.getsize(icon_path)} bytes")
    try:
        # Load and set icon
        img = Image.open(icon_path)
        print(f"Image mode: {img.mode}, Size: {img.size}")
        
        photo = ImageTk.PhotoImage(img)
        root.wm_iconphoto(False, photo)
        print("Icon set via wm_iconphoto!")
        
        # Also try bitmap logic just in case
        # root.iconbitmap("app.ico") 
        
    except Exception as e:
        print(f"Error setting icon: {e}")
else:
    print("app.png NOT found in current directory!")
    print(f"Current Dir: {os.getcwd()}")

label = ctk.CTkLabel(root, text="看看左上角图标变了吗？\nCheck the top-left icon.", font=("Arial", 20))
label.pack(expand=True)

root.mainloop()
