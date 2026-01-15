import sys
import os
import json
import keyboard
import time

print("--- DIAGNOSTIC START ---")

# 1. Check Config
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    print("Mode: Frozen (Exe)")
else:
    BASE_DIR = os.path.abspath(".")
    print("Mode: Source (Script)")

config_path = os.path.join(BASE_DIR, 'config.json')
print(f"Looking for config at: {config_path}")

if os.path.exists(config_path):
    print("Config file FOUND.")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Config content: {data}")
            print(f"Hotkey setting: {data.get('hotkey')}")
    except Exception as e:
        print(f"Error reading config: {e}")
else:
    print("Config file NOT FOUND. App will use defaults (ctrl+alt+v).")

# 2. Check Hotkey Registration
target_key = "F9"
print(f"\nAttempting to register global hotkey: {target_key}")
try:
    keyboard.add_hotkey(target_key, lambda: print("Hotkey triggered!"))
    print(f"SUCCESS: '{target_key}' registered successfully.")
    print("This indicates the system allows this key binding.")
    keyboard.unhook_all_hotkeys()
except ImportError:
    print("ERROR: 'keyboard' module not installed properly.")
except OSError as e:
    print(f"ERROR: OS denied permission. Admin rights likely needed.\nDetails: {e}")
except Exception as e:
    print(f"ERROR: unexpected error registering hotkey: {e}")

print("--- DIAGNOSTIC END ---")
