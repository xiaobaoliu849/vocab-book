import customtkinter as ctk
import tkinter as tk

def on_left_click():
    print("Left click command executed")

def on_right_click(event):
    print("Right click detected!")
    menu.tk_popup(event.x_root, event.y_root)

app = ctk.CTk()
app.geometry("400x300")

btn = ctk.CTkButton(app, text="Test Right Click", command=on_left_click)
btn.pack(pady=50)

# Bind right click
btn.bind("<Button-3>", on_right_click)
btn.bind("<Button-2>", on_right_click) # For macOS

menu = tk.Menu(app, tearoff=0)
menu.add_command(label="Context Menu Item", command=lambda: print("Menu item clicked"))

app.mainloop()
