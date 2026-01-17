import os
import sys
import json
import customtkinter as ctk

# Base paths
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = os.path.dirname(sys.executable)
    # Resource path (for bundled assets like images inside the exe)
    RESOURCE_DIR = sys._MEIPASS
else:
    # Running from source
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESOURCE_DIR = BASE_DIR

CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
SOUNDS_DIR = os.path.join(BASE_DIR, 'sounds')
DB_PATH = os.path.join(BASE_DIR, 'vocab.db')

# UI Constants
THEME_COLOR = "blue"
FONT_NORMAL = ("Microsoft YaHei UI", 15)
FONT_BOLD = ("Microsoft YaHei UI", 15, "bold")
FONT_LARGE = ("Microsoft YaHei UI", 28, "bold")

# App Version - 从 version.json 读取
APP_VERSION = "1.0"
# 优先从资源目录读取（打包后版本文件在临时解压目录）
_version_file = os.path.join(RESOURCE_DIR, 'version.json')
if not os.path.exists(_version_file):
    # 开发环境：尝试从项目根目录读取
    _version_file = os.path.join(BASE_DIR, 'version.json')
if os.path.exists(_version_file):
    try:
        with open(_version_file, 'r', encoding='utf-8') as f:
            _version_data = json.load(f)
            APP_VERSION = _version_data.get("version", "1.0")
            del _version_data
    except Exception:
        pass
    del _version_file

def init_resources():
    """Ensure necessary directories exist"""
    if not os.path.exists(SOUNDS_DIR):
        os.makedirs(SOUNDS_DIR)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return get_default_config()


def get_default_config():
    """返回默认配置"""
    return {
        "hotkey": "ctrl+alt+v",
        "close_action": "ask",  # "ask" | "minimize" | "exit"
        "reminder_interval": 30,  # 复习提醒间隔（分钟）
        # 多词典配置
        "dict_sources": {
            "youdao": True,    # 有道词典（默认开启）
            "cambridge": True, # 剑桥词典（默认开启）
            "bing": True,      # Bing 词典（默认开启）
            "freedict": True,  # Free Dictionary API（默认开启）
        },
        "dict_primary": "youdao",  # 主词典（用于保存到数据库）
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Config save error: {e}")

def setup_theme(config=None):
    if config is None:
        config = load_config()

    ctk.set_default_color_theme(THEME_COLOR)
    saved_theme = config.get("theme", "Light")
    ctk.set_appearance_mode(saved_theme)
