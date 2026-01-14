"""
智能生词本 v3.0 - SQLite 数据库版本
=====================================
主要变更:
1. 数据存储从 JSON 迁移到 SQLite 数据库
2. 使用 DatabaseManager 进行所有 CRUD 操作
3. 保留原有 UI 和功能不变
"""
import customtkinter as ctk
import os
import threading
import requests
import keyboard
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from tkinter import messagebox
from PIL import Image

# 导入数据库管理器
from database import DatabaseManager

# Configuration
CONFIG_FILE = 'config.json'
SOUNDS_DIR = 'sounds'
THEME_COLOR = "blue"
FONT_NORMAL = ("Microsoft YaHei UI", 15)
FONT_BOLD = ("Microsoft YaHei UI", 15, "bold")
FONT_LARGE = ("Microsoft YaHei UI", 28, "bold")

# Ensure sounds directory exists
if not os.path.exists(SOUNDS_DIR):
    os.makedirs(SOUNDS_DIR)

# Try to import pygame for audio
AUDIO_AVAILABLE = False
try:
    import pygame
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except ImportError:
    pass

# 加载配置 (仍使用 JSON)
import json
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"hotkey": "ctrl+alt+v"}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Config save error: {e}")

ctk.set_default_color_theme(THEME_COLOR)

# 加载配置并设置主题
_init_config = load_config()
_saved_theme = _init_config.get("theme", "Light")
ctk.set_appearance_mode(_saved_theme)


class VocabApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 初始化数据库
        self.db = DatabaseManager()

        # 从数据库加载所有单词 (保留 vocab_list 兼容旧逻辑)
        self.vocab_list = self.db.get_all_words()

        # 分页和过滤状态
        self.page_size = 20                    # 每页显示数量
        self.current_page = 1                  # 当前页码 (1-indexed)
        self.total_pages = 1                   # 总页数
        self.filtered_vocab_list = []          # 过滤后的单词列表
        self.search_query = ""                 # 搜索关键词
        self.status_filter = "全部"            # 状态筛选
        self.list_search_timer = None          # 搜索防抖定时器
        self.row_pool = []                     # Widget 池

        # 设置标题（显示单词数量）
        word_count = len(self.vocab_list)
        self.title(f"我的智能生词本 v3.0 (SQLite) - {word_count} 个单词")
        self.geometry("1000x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 加载配置
        self.config = load_config()
        self.current_hotkey = self.config.get("hotkey", "ctrl+alt+v")

        # Layout: Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="📖 生词本", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.btn_add = ctk.CTkButton(self.sidebar_frame, text="📝 记单词", command=lambda: self.show_frame("add"))
        self.btn_add.grid(row=1, column=0, padx=20, pady=10)

        self.btn_list = ctk.CTkButton(self.sidebar_frame, text="📚 单词列表", command=lambda: self.show_frame("list"))
        self.btn_list.grid(row=2, column=0, padx=20, pady=10)

        self.btn_review = ctk.CTkButton(self.sidebar_frame, text="🧠 智能复习", command=lambda: self.show_frame("review"))
        self.btn_review.grid(row=3, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ 设置", fg_color="gray", hover_color="gray30", command=lambda: self.show_frame("settings"))
        self.btn_settings.grid(row=4, column=0, padx=20, pady=10)

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Initialize Frames
        self.frames = {}
        self.create_add_frame()
        self.create_list_frame()
        self.create_review_frame()
        self.create_settings_frame()

        self.show_frame("add")

        # Global Hotkey
        self.setup_hotkey()

        # Handle Close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def reload_vocab_list(self):
        """从数据库重新加载词汇表"""
        self.vocab_list = self.db.get_all_words()
        # 更新标题栏的单词数量
        self.update_title()

    def update_title(self):
        """更新窗口标题显示单词数量"""
        word_count = len(self.vocab_list)
        self.title(f"我的智能生词本 v3.0 (SQLite) - {word_count} 个单词")

    def setup_hotkey(self):
        try:
            try:
                keyboard.unhook_all_hotkeys()
            except AttributeError:
                pass
            except Exception as e:
                print(f"Unhook error: {e}")
            keyboard.add_hotkey(self.current_hotkey, self.on_hotkey_triggered)
        except Exception as e:
            print(f"Hotkey setup error: {e}")

    def on_hotkey_triggered(self):
        try:
            keyboard.send('ctrl+c')
            time.sleep(0.1)
        except Exception as e:
            print(f"Auto-copy failed: {e}")
        self.after(0, self.bring_to_front)

    def bring_to_front(self):
        try:
            self.iconify()
            self.deiconify()
            self.state('normal')
            self.attributes('-topmost', True)
            self.lift()
            self.focus_force()
            self.after(200, lambda: self.attributes('-topmost', False))
            self.show_frame("add")
            self.entry_word.focus_set()
            try:
                clip_text = self.clipboard_get().strip()
                if clip_text and len(clip_text) < 50:
                    current_text = self.entry_word.get().strip()
                    if clip_text.lower() != current_text.lower():
                        self.entry_word.delete(0, "end")
                        self.entry_word.insert(0, clip_text)
                        self.after(100, self.start_search)
            except:
                pass
        except Exception as e:
            print(f"Wake error: {e}")

    def show_frame(self, name):
        for frame in self.frames.values():
            frame.pack_forget()
        if name == "list":
            self.refresh_list()
        elif name == "review":
            self.start_review()
        elif name == "settings":
            self.refresh_settings()
        self.frames[name].pack(fill="both", expand=True)

    def play_audio(self, word, button=None):
        """播放单词发音，支持按钮状态反馈"""
        if not AUDIO_AVAILABLE:
            messagebox.showinfo("提示", "音频组件未安装！")
            return

        def _play():
            try:
                # 更新按钮状态为"加载中"
                if button:
                    self.after(0, lambda: button.configure(text="⏳", fg_color="orange"))

                file_path = os.path.join(SOUNDS_DIR, f"{word}.mp3")
                if not os.path.exists(file_path):
                    url = f"https://dict.youdao.com/dictvoice?audio={word}&type=2"
                    r = requests.get(url, timeout=5)
                    with open(file_path, 'wb') as f:
                        f.write(r.content)

                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()

                # 更新按钮状态为"播放中"
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="green"))

            except Exception as e:
                print(f"Play error: {e}")
                # 播放失败时恢复按钮
                if button:
                    self.after(0, lambda: button.configure(text="🔊", fg_color="gray"))

        threading.Thread(target=_play, daemon=True).start()

    def translate_sentence(self, text):
        try:
            url = "http://m.youdao.com/translate"
            data = {"inputtext": text, "type": "AUTO"}
            headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)'}
            r = requests.post(url, data=data, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            res_ul = soup.find('ul', id='translateResult')
            if res_ul:
                tgt = res_ul.find('li')
                if tgt:
                    return tgt.get_text().strip()
            generate_div = soup.find('div', class_='generate')
            if generate_div:
                return generate_div.get_text().strip()
        except Exception as e:
            print(f"Translation error: {e}")
        return "翻译获取失败，请手动输入"


    # --- ADD FRAME ---
    def create_add_frame(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["add"] = frame

        top_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_frame.pack(fill="x", pady=(20, 10))

        self.entry_word = ctk.CTkEntry(top_frame, placeholder_text="输入单词...", width=400, height=50, font=("Microsoft YaHei UI", 16))
        self.entry_word.pack(side="left", padx=(0, 15))
        self.entry_word.bind("<Return>", lambda event: self.start_search())

        self.btn_search = ctk.CTkButton(top_frame, text="🔍 查询", width=100, height=50, font=("Microsoft YaHei UI", 15, "bold"), command=self.start_search)
        self.btn_search.pack(side="left", padx=5)

        self.btn_play_result = ctk.CTkButton(top_frame, text="🔊", width=60, height=50, fg_color="green", font=("Microsoft YaHei UI", 18), state="disabled")
        self.btn_play_result.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(frame, text="", text_color="gray", font=("Microsoft YaHei UI", 13))
        self.status_label.pack(pady=(0, 10), anchor="w", padx=5)

        ctk.CTkLabel(frame, text="📖 释义", font=("Microsoft YaHei UI", 14, "bold"), text_color="gray50").pack(anchor="w", padx=5)

        self.result_textbox = ctk.CTkTextbox(frame, width=800, height=220, font=("Microsoft YaHei UI", 15), fg_color=("white", "gray20"), border_width=1, border_color="gray80")
        self.result_textbox.pack(pady=(5, 20), fill="x")
        self.result_textbox.insert("0.0", "\n  等待查询...")
        self.result_textbox.configure(state="disabled")

        ctx_frame = ctk.CTkFrame(frame, fg_color=("white", "gray25"), border_width=1, border_color="gray75", corner_radius=10)
        ctx_frame.pack(fill="both", expand=True, pady=(0, 20))

        head_frame = ctk.CTkFrame(ctx_frame, fg_color="transparent")
        head_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(head_frame, text="✍️ 来源语境 (粘贴原句)", font=("Microsoft YaHei UI", 14, "bold"), text_color="#3B8ED0").pack(side="left")

        self.btn_context_save = ctk.CTkButton(head_frame, text="💾 保存语境", width=100, height=30,
                                            fg_color="#3B8ED0", font=("Microsoft YaHei UI", 13, "bold"),
                                            command=self.save_context)
        self.btn_context_save.pack(side="right")

        self.txt_context_en = ctk.CTkTextbox(ctx_frame, height=120, font=("Microsoft YaHei UI", 15), fg_color="transparent", border_width=0)
        self.txt_context_en.pack(fill="x", padx=15, pady=(0, 5))

        line = ctk.CTkFrame(ctx_frame, height=1, fg_color="gray85")
        line.pack(fill="x", padx=15, pady=5)

        self.txt_context_cn = ctk.CTkTextbox(ctx_frame, height=80, font=("Microsoft YaHei UI", 14), text_color=("gray30", "gray70"), fg_color="transparent", border_width=0)
        self.txt_context_cn.pack(fill="x", padx=15, pady=(0, 15))
        self.txt_context_cn.insert("0.0", "待粘贴例句... (自动翻译)")
        self.txt_context_cn.configure(state="disabled")

        self.translate_timer = None
        self.last_translated_text = ""
        self.txt_context_en.bind("<KeyRelease>", self.schedule_translation)
        self.txt_context_en.bind("<FocusOut>", self.schedule_translation)
        self.txt_context_en.bind("<Control-v>", self.schedule_translation)

    def schedule_translation(self, event=None):
        if self.translate_timer:
            self.after_cancel(self.translate_timer)
        self.translate_timer = self.after(800, self.auto_translate_context)

    def auto_translate_context(self):
        text = self.txt_context_en.get("0.0", "end").strip()
        if not text or text == self.last_translated_text or len(text) < 3:
            return
        self.last_translated_text = text
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        self.txt_context_cn.insert("0.0", "⏳ 正在翻译...")
        self.txt_context_cn.configure(state="disabled")
        threading.Thread(target=self.run_translation, args=(text,), daemon=True).start()

    def run_translation(self, text):
        trans = self.translate_sentence(text)
        self.after(0, lambda: self.update_trans_box(trans))

    def update_trans_box(self, text):
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        self.txt_context_cn.insert("0.0", text)

    def save_context(self):
        """保存语境 - 使用数据库"""
        word = self.entry_word.get().strip() or (self.vocab_list[0]['word'] if self.vocab_list else "")
        if not word:
            return

        ctx_en = self.txt_context_en.get("0.0", "end").strip()
        ctx_cn = self.txt_context_cn.get("0.0", "end").strip()

        if not ctx_cn or "⏳" in ctx_cn or "待粘贴" in ctx_cn:
            ctx_cn = self.translate_sentence(ctx_en)
            self.update_trans_box(ctx_cn)

        # 使用数据库更新
        self.db.update_context(word, ctx_en, ctx_cn)
        self.reload_vocab_list()

        messagebox.showinfo("成功", "例句已更新！")
        self.txt_context_en.delete("0.0", "end")
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        self.last_translated_text = ""

    def start_search(self):
        word = self.entry_word.get().strip()
        if not word:
            return
        self.status_label.configure(text="查询中...", text_color="gray")
        self.btn_search.configure(state="disabled")
        self.btn_play_result.configure(state="disabled", fg_color="gray")
        self.txt_context_en.delete("0.0", "end")
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        threading.Thread(target=self.search_word_thread, args=(word,), daemon=True).start()

    def search_word_thread(self, word):
        # 检查数据库中是否已存在
        existing = self.db.get_word(word)
        if existing:
            display = f"{existing['word']}  {existing.get('phonetic','')}\n\n[释义]\n{existing['meaning']}\n\n[例句]\n{existing['example']}"
            self.after(0, lambda: self.display_existing_word(existing, display))
            return

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            url = f"https://dict.youdao.com/w/eng/{word}"
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                if soup.find('div', class_='error-wrapper'):
                    self.after(0, lambda: self.search_complete(None, "未找到该单词", None))
                    return

                phonetic = ""
                phs = soup.find_all('span', class_='phonetic')
                if phs:
                    phonetic = phs[1].get_text() if len(phs) > 1 else phs[0].get_text()

                meaning = ""
                trans = soup.find('div', class_='trans-container')
                if trans and trans.find('ul'):
                    meaning = "\n".join([li.get_text() for li in trans.find('ul').find_all('li') if not li.get('class')])
                if not meaning:
                    meaning = "暂无释义"

                example = ""
                bi = soup.find('div', id='bilingual')
                if bi and bi.find('li'):
                    p = bi.find('li').find_all('p')
                    if len(p) >= 2:
                        example = f"{p[0].get_text(separator=' ', strip=True)}\n{p[1].get_text(separator=' ', strip=True)}"

                new_word = {
                    "word": word,
                    "phonetic": phonetic,
                    "meaning": meaning,
                    "example": example,
                    "date": datetime.now().strftime('%Y-%m-%d'),
                }

                # 使用数据库添加
                self.db.add_word(new_word)
                self.reload_vocab_list()

                display = f"{word}  {phonetic}\n\n[释义]\n{meaning}\n\n[例句]\n{example}"
                self.after(0, lambda: self.search_complete(display, "✅ 已保存", word))
            else:
                self.after(0, lambda: self.search_complete(None, "网络错误", None))
        except Exception as e:
            self.after(0, lambda: self.search_complete(None, f"错误: {str(e)}", None))


    def display_existing_word(self, item, text):
        self.btn_search.configure(state="normal")
        rc = item.get('review_count', 0)
        self.status_label.configure(text=f"✅ 已存在 (复习: {rc}次)", text_color="green")

        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("0.0", "end")
        self.result_textbox.insert("0.0", text)
        self.result_textbox.configure(state="disabled")

        self.txt_context_en.delete("0.0", "end")
        if item.get('context_en'):
            self.txt_context_en.insert("0.0", item['context_en'])

        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        if item.get('context_cn'):
            self.txt_context_cn.insert("0.0", item['context_cn'])
        else:
            self.txt_context_cn.insert("0.0", "待粘贴例句...")
            self.txt_context_cn.configure(state="disabled")

        self.entry_word.delete(0, "end")
        self.btn_play_result.configure(state="normal", fg_color="green", command=lambda: self.play_audio(item['word']))
        self.after(500, lambda: self.play_audio(item['word']))

    def search_complete(self, text, status, word):
        self.btn_search.configure(state="normal")
        self.status_label.configure(text=status, text_color="green" if "✅" in status else "red")

        if text:
            self.result_textbox.configure(state="normal")
            self.result_textbox.delete("0.0", "end")
            self.result_textbox.insert("0.0", text)
            self.result_textbox.configure(state="disabled")
            self.entry_word.delete(0, "end")
            self.btn_play_result.configure(state="normal", fg_color="green", command=lambda: self.play_audio(word))
            self.after(500, lambda: self.play_audio(word))

    # --- LIST FRAME ---
    def create_list_frame(self):
        self.frames["list"] = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        # === 工具栏: 搜索 + 筛选 ===
        toolbar_frame = ctk.CTkFrame(self.frames["list"], fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=5, pady=(0, 10))

        # 搜索输入框
        self.list_search_entry = ctk.CTkEntry(
            toolbar_frame,
            placeholder_text="🔍 搜索单词或释义...",
            width=280,
            height=38,
            font=("Microsoft YaHei UI", 14)
        )
        self.list_search_entry.pack(side="left", padx=(0, 8))
        self.list_search_entry.bind("<KeyRelease>", self.on_list_search_input)
        self.list_search_entry.bind("<Return>", lambda e: self.execute_list_search())

        # 清除搜索按钮
        self.btn_clear_search = ctk.CTkButton(
            toolbar_frame, text="✕", width=38, height=38,
            fg_color="transparent", text_color="gray",
            hover_color=("gray90", "gray25"),
            command=self.clear_list_search
        )
        self.btn_clear_search.pack(side="left", padx=(0, 15))

        # 状态筛选下拉框
        self.filter_options = ["全部", "待复习", "已掌握", "新单词", "学习中"]
        self.filter_dropdown = ctk.CTkOptionMenu(
            toolbar_frame,
            values=self.filter_options,
            width=110,
            height=38,
            font=("Microsoft YaHei UI", 13),
            command=self.on_filter_change
        )
        self.filter_dropdown.set("全部")
        self.filter_dropdown.pack(side="left")

        # 结果计数标签
        self.lbl_results_count = ctk.CTkLabel(
            toolbar_frame, text="",
            font=("Microsoft YaHei UI", 12),
            text_color="gray"
        )
        self.lbl_results_count.pack(side="right", padx=10)

        # === 可滚动列表 ===
        self.list_scroll = ctk.CTkScrollableFrame(
            self.frames["list"],
            label_text="单词列表",
            label_font=("Microsoft YaHei UI", 14, "bold")
        )
        self.list_scroll.pack(fill="both", expand=True)

        # 预创建 Widget 池
        self.row_pool = []
        for i in range(self.page_size):
            row = self.create_row_widget()
            self.row_pool.append(row)

        # === 分页控件 ===
        self.create_pagination_controls()

    def create_row_widget(self):
        """创建一个可复用的行 Widget"""
        row_frame = ctk.CTkFrame(self.list_scroll, fg_color="transparent")

        status_label = ctk.CTkLabel(row_frame, text="", width=70, font=("Arial", 12, "bold"))
        status_label.pack(side="left")

        word_btn = ctk.CTkButton(
            row_frame, text="", anchor="w",
            font=("Microsoft YaHei UI", 14),
            fg_color="transparent",
            text_color=("black", "white"),
            hover_color=("gray90", "gray25")
        )
        word_btn.pack(side="left", fill="x", expand=True, padx=5)

        play_btn = ctk.CTkButton(
            row_frame, text="🔊", width=35,
            fg_color="transparent", text_color="green",
            hover_color=("gray90", "gray25"),
            border_width=1, border_color="green"
        )
        play_btn.pack(side="left", padx=2)

        delete_btn = ctk.CTkButton(
            row_frame, text="🗑️", width=35,
            fg_color="transparent", text_color="red",
            hover_color=("gray90", "gray25"),
            border_width=1, border_color="red"
        )
        delete_btn.pack(side="left", padx=2)

        return {
            'frame': row_frame,
            'status': status_label,
            'word_btn': word_btn,
            'play_btn': play_btn,
            'delete_btn': delete_btn
        }

    def update_row_widget(self, row, item, now_ts):
        """更新行 Widget 的数据"""
        # 计算状态图标和颜色
        stage = item.get('stage', 0)
        next_time = item.get('next_review_time', 0)

        if item.get('mastered'):
            status_icon, color = "🏆", "green"
        elif next_time == 0:
            status_icon, color = "🆕", "gray"
        elif next_time <= now_ts:
            status_icon, color = "🔴", "red"
        else:
            status_icon, color = "🟢", "blue"

        row['status'].configure(text=f"{status_icon} Lv.{stage}", text_color=color)

        # 更新单词按钮
        meaning_lines = item['meaning'].splitlines()
        m_text = meaning_lines[0][:15] + "..." if meaning_lines and len(meaning_lines[0]) > 15 else (meaning_lines[0] if meaning_lines else "")
        btn_text = f"{item['word']}  {item.get('phonetic', '')}   {m_text}"
        row['word_btn'].configure(text=btn_text, command=lambda x=item: self.view_word_detail(x))

        # 更新操作按钮 - 传入按钮引用用于状态反馈
        play_btn = row['play_btn']
        row['play_btn'].configure(command=lambda w=item['word'], b=play_btn: self.play_audio(w, b))
        row['delete_btn'].configure(command=lambda w=item['word']: self.delete_word(w))

    def create_pagination_controls(self):
        """创建底部分页栏"""
        self.pagination_frame = ctk.CTkFrame(self.frames["list"], fg_color="transparent")
        self.pagination_frame.pack(fill="x", pady=(10, 5))

        # 左侧：分页按钮
        nav_frame = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        nav_frame.pack(side="left")

        # 上一页按钮
        self.btn_prev = ctk.CTkButton(
            nav_frame, text="◀ 上一页", width=90, height=32,
            font=("Microsoft YaHei UI", 12),
            command=self.go_prev_page
        )
        self.btn_prev.pack(side="left", padx=5)

        # 页码信息
        self.lbl_page_info = ctk.CTkLabel(
            nav_frame, text="第 1 / 1 页",
            font=("Microsoft YaHei UI", 13, "bold"),
            width=100
        )
        self.lbl_page_info.pack(side="left", padx=10)

        # 下一页按钮
        self.btn_next = ctk.CTkButton(
            nav_frame, text="下一页 ▶", width=90, height=32,
            font=("Microsoft YaHei UI", 12),
            command=self.go_next_page
        )
        self.btn_next.pack(side="left", padx=5)

        # 右侧：每页数量选择
        size_frame = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        size_frame.pack(side="right")

        ctk.CTkLabel(
            size_frame, text="每页:",
            font=("Microsoft YaHei UI", 12)
        ).pack(side="left", padx=(0, 5))

        self.page_size_dropdown = ctk.CTkOptionMenu(
            size_frame,
            values=["15", "20", "30", "50"],
            width=70, height=32,
            font=("Microsoft YaHei UI", 12),
            command=self.on_page_size_change
        )
        self.page_size_dropdown.set(str(self.page_size))
        self.page_size_dropdown.pack(side="left")

    def view_word_detail(self, item):
        self.show_frame("add")
        display = f"{item['word']}  {item.get('phonetic','')}\n\n[释义]\n{item['meaning']}\n\n[例句]\n{item['example']}"
        self.display_existing_word(item, display)

    # === 搜索和过滤方法 ===
    def on_list_search_input(self, event=None):
        """搜索输入防抖处理"""
        if self.list_search_timer:
            self.after_cancel(self.list_search_timer)
        self.list_search_timer = self.after(300, self.execute_list_search)

    def execute_list_search(self):
        """执行搜索"""
        self.search_query = self.list_search_entry.get().strip()
        self.current_page = 1
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def clear_list_search(self):
        """清空搜索框"""
        self.list_search_entry.delete(0, "end")
        self.search_query = ""
        self.current_page = 1
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def on_filter_change(self, value):
        """状态筛选变化"""
        self.status_filter = value
        self.current_page = 1
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def match_status_filter(self, item, now_ts):
        """检查单词是否匹配当前状态筛选"""
        status = self.status_filter

        if status == "全部":
            return True
        elif status == "待复习":
            return not item.get('mastered') and item.get('next_review_time', 0) <= now_ts and item.get('next_review_time', 0) != 0
        elif status == "已掌握":
            return item.get('mastered', False)
        elif status == "新单词":
            return item.get('next_review_time', 0) == 0
        elif status == "学习中":
            return not item.get('mastered') and item.get('next_review_time', 0) > now_ts
        return True

    def sort_vocab_list(self, items, now_ts):
        """按复习优先级排序：待复习 > 新单词 > 学习中 > 已掌握"""
        def sort_key(item):
            if item.get('mastered'):
                return (3, 0)
            next_time = item.get('next_review_time', 0)
            if next_time == 0:
                return (1, 0)  # 新单词
            elif next_time <= now_ts:
                return (0, next_time)  # 待复习
            else:
                return (2, next_time)  # 学习中
        return sorted(items, key=sort_key)

    def apply_filters(self):
        """应用搜索和状态筛选"""
        query = self.search_query.lower().strip()
        now_ts = datetime.now().timestamp()

        result = []
        for item in self.vocab_list:
            # 状态筛选
            if not self.match_status_filter(item, now_ts):
                continue

            # 搜索筛选
            if query:
                word_match = query in item['word'].lower()
                meaning_match = query in item.get('meaning', '').lower()
                if not (word_match or meaning_match):
                    continue

            result.append(item)

        # 排序
        self.filtered_vocab_list = self.sort_vocab_list(result, now_ts)

        # 计算分页
        total_items = len(self.filtered_vocab_list)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)

        # 调整当前页
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        # 更新结果计数
        self.lbl_results_count.configure(text=f"找到 {total_items} 个单词")

    def render_current_page(self):
        """渲染当前页的单词"""
        # 先隐藏所有行
        for row in self.row_pool:
            row['frame'].pack_forget()

        if not self.filtered_vocab_list:
            # 显示空提示（复用第一行显示提示）
            if self.row_pool:
                self.row_pool[0]['status'].configure(text="", text_color="gray")
                self.row_pool[0]['word_btn'].configure(text="空空如也，快去添加单词吧！", command=lambda: self.show_frame("add"))
                self.row_pool[0]['play_btn'].pack_forget()
                self.row_pool[0]['delete_btn'].pack_forget()
                self.row_pool[0]['frame'].pack(fill="x", pady=20, padx=5)
            return

        # 计算当前页数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        page_items = self.filtered_vocab_list[start_idx:end_idx]

        now_ts = datetime.now().timestamp()

        # 确保 row_pool 足够
        while len(self.row_pool) < len(page_items):
            row = self.create_row_widget()
            self.row_pool.append(row)

        # 更新并显示行
        for i, item in enumerate(page_items):
            row = self.row_pool[i]
            # 确保按钮可见
            row['play_btn'].pack(side="left", padx=2)
            row['delete_btn'].pack(side="left", padx=2)
            # 更新数据
            self.update_row_widget(row, item, now_ts)
            row['frame'].pack(fill="x", pady=2, padx=5)

        # 滚动到顶部
        try:
            self.list_scroll._parent_canvas.yview_moveto(0)
        except:
            pass

    def update_pagination_controls(self):
        """更新分页控件状态"""
        # 更新页码信息
        self.lbl_page_info.configure(text=f"第 {self.current_page} / {self.total_pages} 页")

        # 更新按钮状态
        if self.current_page <= 1:
            self.btn_prev.configure(state="disabled", fg_color="gray")
        else:
            self.btn_prev.configure(state="normal", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

        if self.current_page >= self.total_pages:
            self.btn_next.configure(state="disabled", fg_color="gray")
        else:
            self.btn_next.configure(state="normal", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

    def go_prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.render_current_page()
            self.update_pagination_controls()

    def go_next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.render_current_page()
            self.update_pagination_controls()

    def on_page_size_change(self, value):
        """每页数量变化"""
        self.page_size = int(value)
        self.current_page = 1
        self.apply_filters()

        # 确保 row_pool 足够
        while len(self.row_pool) < self.page_size:
            row = self.create_row_widget()
            self.row_pool.append(row)

        self.render_current_page()
        self.update_pagination_controls()

    def refresh_list(self):
        """刷新列表视图"""
        self.reload_vocab_list()
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def delete_word(self, word):
        """删除单词 - 使用数据库"""
        if messagebox.askyesno("删除确认", f"确定要删除单词 \"{word}\" 吗？\n\n此操作不可撤销。"):
            self.db.delete_word(word)
            self.reload_vocab_list()
            self.apply_filters()
            self.render_current_page()
            self.update_pagination_controls()

    # --- REVIEW FRAME ---
    def create_review_frame(self):
        self.frames["review"] = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        # 复习模式状态
        self.review_mode = "flashcard"  # "flashcard" 或 "spelling"

        # === 顶部：模式切换 + 进度 ===
        top_frame = ctk.CTkFrame(self.frames["review"], fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(10, 0))

        # 模式切换按钮组
        mode_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        mode_frame.pack(side="left")

        self.btn_mode_flashcard = ctk.CTkButton(
            mode_frame, text="📖 闪卡模式", width=100, height=32,
            font=("Microsoft YaHei UI", 12, "bold"),
            fg_color="#3B8ED0",
            command=lambda: self.switch_review_mode("flashcard")
        )
        self.btn_mode_flashcard.pack(side="left", padx=(0, 5))

        self.btn_mode_spelling = ctk.CTkButton(
            mode_frame, text="✍️ 拼写模式", width=100, height=32,
            font=("Microsoft YaHei UI", 12, "bold"),
            fg_color="gray",
            command=lambda: self.switch_review_mode("spelling")
        )
        self.btn_mode_spelling.pack(side="left")

        # 进度显示栏
        progress_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        progress_frame.pack(side="right")

        self.lbl_review_progress = ctk.CTkLabel(
            progress_frame,
            text="待复习: 0 个",
            font=("Microsoft YaHei UI", 14),
            text_color="gray"
        )
        self.lbl_review_progress.pack(side="left", padx=(0, 10))

        self.review_progress_bar = ctk.CTkProgressBar(progress_frame, width=200, height=8)
        self.review_progress_bar.pack(side="left")
        self.review_progress_bar.set(0)

        # === 闪卡模式卡片 ===
        self.card = ctk.CTkFrame(self.frames["review"], height=400, fg_color=("gray90", "gray20"))
        self.card.pack(fill="x", pady=20, padx=20)
        self.card.pack_propagate(False)

        self.lbl_rw = ctk.CTkLabel(self.card, text="准备开始", font=FONT_LARGE)
        self.lbl_rw.pack(pady=(40, 10))

        self.btn_rp = ctk.CTkButton(self.card, text="🔊", width=40, fg_color="green", command=lambda: None)
        self.btn_rp.pack(pady=5)

        self.txt_rm = ctk.CTkTextbox(self.card, width=500, height=200, font=FONT_NORMAL, fg_color="transparent")
        self.txt_rm.pack(pady=10, fill="both", expand=True, padx=20)

        self.btn_rev = ctk.CTkButton(self.frames["review"], text="显示释义 (Space)", font=FONT_BOLD, width=200, height=45, command=self.reveal_meaning)
        self.btn_rev.pack(pady=20)

        self.act_frame = ctk.CTkFrame(self.frames["review"], fg_color="transparent")

        # SM-2 风格的三级反馈按钮
        ctk.CTkButton(self.act_frame, text="忘记 (1)", fg_color="#F44336", width=100, height=40,
                     command=lambda: self.process_review_sm2(1)).pack(side="left", padx=10)

        ctk.CTkButton(self.act_frame, text="模糊 (2)", fg_color="#FF9800", width=100, height=40,
                     command=lambda: self.process_review_sm2(3)).pack(side="left", padx=10)

        ctk.CTkButton(self.act_frame, text="熟悉 (3)", fg_color="#4CAF50", width=100, height=40,
                     command=lambda: self.process_review_sm2(5)).pack(side="left", padx=10)


        # === 拼写模式卡片 ===
        self.spelling_card = ctk.CTkFrame(self.frames["review"], height=550, fg_color=("gray90", "gray20"))
        self.spelling_card.pack_propagate(False)

        # 释义提示区域
        self.lbl_spelling_hint = ctk.CTkLabel(
            self.spelling_card, text="根据释义拼写单词",
            font=("Microsoft YaHei UI", 14), text_color="gray"
        )
        self.lbl_spelling_hint.pack(pady=(20, 5))

        self.txt_spelling_meaning = ctk.CTkTextbox(
            self.spelling_card, width=600, height=260,
            font=("Microsoft YaHei UI", 15),
            fg_color="transparent"
        )
        self.txt_spelling_meaning.pack(pady=10, padx=20)
        self.txt_spelling_meaning.configure(state="disabled")

        # 发音按钮
        self.btn_spelling_play = ctk.CTkButton(
            self.spelling_card, text="🔊 听发音", width=100, height=35,
            fg_color="green", font=("Microsoft YaHei UI", 13),
            command=lambda: None
        )
        self.btn_spelling_play.pack(pady=5)

        # 拼写输入区域
        input_frame = ctk.CTkFrame(self.spelling_card, fg_color="transparent")
        input_frame.pack(pady=20, fill="x", padx=40)

        self.entry_spelling = ctk.CTkEntry(
            input_frame, placeholder_text="输入单词拼写...",
            width=350, height=50, font=("Microsoft YaHei UI", 18),
            justify="center"
        )
        self.entry_spelling.pack(side="left", padx=(0, 10))
        self.entry_spelling.bind("<Return>", lambda e: self.check_spelling())

        self.btn_check_spelling = ctk.CTkButton(
            input_frame, text="✓ 检查", width=80, height=50,
            font=("Microsoft YaHei UI", 14, "bold"),
            fg_color="#4CAF50", hover_color="#45a049",
            command=self.check_spelling
        )
        self.btn_check_spelling.pack(side="left")

        # 结果反馈区域
        self.spelling_result_frame = ctk.CTkFrame(self.spelling_card, fg_color="transparent")
        self.spelling_result_frame.pack(fill="x", padx=20, pady=10)

        self.lbl_spelling_result = ctk.CTkLabel(
            self.spelling_result_frame, text="",
            font=("Microsoft YaHei UI", 16, "bold")
        )
        self.lbl_spelling_result.pack()

        self.lbl_correct_answer = ctk.CTkLabel(
            self.spelling_result_frame, text="",
            font=("Microsoft YaHei UI", 14)
        )
        self.lbl_correct_answer.pack()

        # 拼写模式下一个按钮
        self.btn_spelling_next = ctk.CTkButton(
            self.frames["review"], text="下一个 (Enter)", width=150, height=45,
            font=("Microsoft YaHei UI", 14, "bold"),
            command=self.spelling_next
        )

    def switch_review_mode(self, mode):
        """切换复习模式"""
        if mode == self.review_mode:
            return

        self.review_mode = mode

        # 更新按钮样式
        if mode == "flashcard":
            self.btn_mode_flashcard.configure(fg_color="#3B8ED0")
            self.btn_mode_spelling.configure(fg_color="gray")
        else:
            self.btn_mode_flashcard.configure(fg_color="gray")
            self.btn_mode_spelling.configure(fg_color="#3B8ED0")

        # 重新开始当前模式
        if self.queue:
            if mode == "flashcard":
                self.spelling_card.pack_forget()
                self.btn_spelling_next.pack_forget()
                self.unbind_all("<Return>") # 解除拼写模式的 Enter 绑定
                self.next_card()
            else:
                self.card.pack_forget()
                self.btn_rev.pack_forget()
                self.act_frame.pack_forget()
                self.next_spelling_card()

    def start_review(self):
        self.reload_vocab_list()
        now_ts = datetime.now().timestamp()
        self.queue = []

        for w in self.vocab_list:
            if w.get('mastered', False):
                continue
            next_time = w.get('next_review_time', 0)
            if next_time <= now_ts:
                self.queue.append(w)

        import random
        random.shuffle(self.queue)

        # 记录初始数量用于进度计算
        self.review_total = len(self.queue)
        self.review_completed = 0

        self.cur_word = None
        self.spelling_checked = False  # 拼写是否已检查

        # 根据当前模式启动
        if self.review_mode == "flashcard":
            self.spelling_card.pack_forget()
            self.btn_spelling_next.pack_forget()
            self.next_card()
        else:
            self.card.pack_forget()
            self.btn_rev.pack_forget()
            self.act_frame.pack_forget()
            self.next_spelling_card()

        # 绑定快捷键
        self.bind_all("<space>", lambda e: self.on_space_key())
        # SM-2 快捷键: 1=忘记, 2=模糊, 3=熟悉
        self.bind_all("1", lambda e: self.process_review_sm2(1) if self.review_mode == "flashcard" and self.act_frame.winfo_viewable() else None)
        self.bind_all("2", lambda e: self.process_review_sm2(3) if self.review_mode == "flashcard" and self.act_frame.winfo_viewable() else None)
        self.bind_all("3", lambda e: self.process_review_sm2(5) if self.review_mode == "flashcard" and self.act_frame.winfo_viewable() else None)

        # 保留旧的左右方向键兼容 (左=忘记, 右=熟悉)
        self.bind_all("<Left>", lambda e: self.process_review_sm2(1) if self.review_mode == "flashcard" and self.act_frame.winfo_viewable() else None)
        self.bind_all("<Right>", lambda e: self.process_review_sm2(5) if self.review_mode == "flashcard" and self.act_frame.winfo_viewable() else None)

    def next_card(self):
        self.txt_rm.configure(state="normal")
        self.txt_rm.delete("0.0", "end")
        self.txt_rm.configure(state="disabled")

        self.btn_rev.pack(pady=20)
        self.act_frame.pack_forget()

        # 更新进度显示
        remaining = len(self.queue)
        if self.review_total > 0:
            progress = self.review_completed / self.review_total
            self.review_progress_bar.set(progress)
            self.lbl_review_progress.configure(
                text=f"进度: {self.review_completed}/{self.review_total}  剩余: {remaining} 个"
            )
        else:
            self.review_progress_bar.set(1)
            self.lbl_review_progress.configure(text="无待复习单词")

        if not self.queue:
            future_count = sum(1 for w in self.vocab_list if not w.get('mastered', False) and w.get('next_review_time', 0) > datetime.now().timestamp())

            msg = "🎉 今日复习完成！"
            if future_count > 0:
                msg += f"\n还有 {future_count} 个单词未到复习时间"

            self.lbl_rw.configure(text=msg)
            self.btn_rev.pack_forget()
            self.review_progress_bar.set(1)
            self.lbl_review_progress.configure(text=f"已完成 {self.review_completed} 个单词")
            self.unbind_all("<space>")
            self.unbind_all("<Left>")
            self.unbind_all("<Right>")
            return

        self.cur_word = self.queue[0]
        self.lbl_rw.configure(text=self.cur_word['word'])
        self.btn_rp.configure(command=lambda: self.play_audio(self.cur_word['word']))
        self.play_audio(self.cur_word['word'])

    def reveal_meaning(self):
        if not self.cur_word or not self.btn_rev.winfo_viewable():
            return

        txt = f"{self.cur_word.get('phonetic','')}\n\n[释义]\n{self.cur_word['meaning']}\n\n[字典例句]\n{self.cur_word['example']}"

        if self.cur_word.get('context_en'):
            txt += f"\n\n[✍️ 来源语境]\n{self.cur_word['context_en']}\n{self.cur_word.get('context_cn','')}"

        self.txt_rm.configure(state="normal")
        self.txt_rm.insert("0.0", txt)
        self.txt_rm.configure(state="disabled")

        self.btn_rev.pack_forget()
        self.act_frame.pack(pady=20)

    def calculate_sm2(self, quality, word_data):
        """
        SM-2 算法实现
        quality: 0-5 (用户反馈)
        word_data: 单词数据字典
        返回: (easiness, interval, repetitions)
        """
        # 获取当前状态，如果是新单词则初始化
        easiness = word_data.get('easiness')
        if easiness is None: easiness = 2.5

        interval = word_data.get('interval')
        if interval is None: interval = 0

        repetitions = word_data.get('repetitions')
        if repetitions is None: repetitions = 0

        # 兼容旧逻辑: 如果是从未进行过 SM-2 复习的单词，但有 stage
        if repetitions == 0 and word_data.get('stage', 0) > 0:
            # 简单的转换估算
            repetitions = word_data['stage']
            interval = [1, 2, 4, 7, 15, 30][min(5, word_data['stage']-1)] if word_data['stage'] <= 6 else 30

        # 1. 更新 Easiness Factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if quality >= 3:
            easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        if easiness < 1.3:
            easiness = 1.3

        # 2. 更新 Repetitions 和 Interval
        if quality < 3:
            # 忘记了，重置
            repetitions = 0
            interval = 1
        else:
            # 记住了
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = int(interval * easiness)

            repetitions += 1

        return easiness, interval, repetitions

    def process_review_sm2(self, quality):
        """处理复习结果 - 使用 SM-2 算法"""
        if not self.cur_word:
            return

        word = self.cur_word['word']

        # 计算新状态
        easiness, interval, repetitions = self.calculate_sm2(quality, self.cur_word)

        # 计算下次复习时间
        next_ts = (datetime.now() + timedelta(days=interval)).timestamp()

        # 使用数据库更新复习状态
        self.db.update_sm2_status(word, easiness, interval, repetitions, next_ts, quality)
        self.reload_vocab_list()

        self.queue.pop(0)

        # 只有记住 (quality >= 3) 时才计入完成数
        if quality >= 3:
            self.review_completed += 1
        else:
            # 忘记了，重新加入队列（短期记忆强化）
            import random
            insert_pos = random.randint(1, len(self.queue)) if len(self.queue) > 0 else 0
            updated_word = self.db.get_word(word)
            if updated_word:
                self.queue.insert(insert_pos, updated_word)

        self.next_card()

    def process_review(self, ok):
        # 兼容旧代码调用，映射到 SM-2
        self.process_review_sm2(5 if ok else 1)

    def on_space_key(self):
        """空格键处理 - 根据模式执行不同操作"""
        if self.review_mode == "flashcard":
            self.reveal_meaning()
        else:
            # 拼写模式：检查或下一个
            if self.spelling_checked:
                self.spelling_next()
            else:
                self.check_spelling()

    # === 拼写模式方法 ===
    def next_spelling_card(self):
        """显示下一个拼写测试卡片"""
        # 重置状态
        self.spelling_checked = False
        self.entry_spelling.configure(border_color="gray", state="normal")  # 先恢复状态
        self.entry_spelling.delete(0, "end")  # 再清空内容
        self.lbl_spelling_result.configure(text="")
        self.lbl_correct_answer.configure(text="")
        self.btn_check_spelling.configure(state="normal", text="✓ 检查")
        self.btn_spelling_next.pack_forget()

        # 更新进度显示
        remaining = len(self.queue)
        if self.review_total > 0:
            progress = self.review_completed / self.review_total
            self.review_progress_bar.set(progress)
            self.lbl_review_progress.configure(
                text=f"进度: {self.review_completed}/{self.review_total}  剩余: {remaining} 个"
            )
        else:
            self.review_progress_bar.set(1)
            self.lbl_review_progress.configure(text="无待复习单词")

        if not self.queue:
            future_count = sum(1 for w in self.vocab_list if not w.get('mastered', False) and w.get('next_review_time', 0) > datetime.now().timestamp())

            self.spelling_card.pack_forget()
            self.card.pack(fill="x", pady=20, padx=20)

            msg = "🎉 今日复习完成！"
            if future_count > 0:
                msg += f"\n还有 {future_count} 个单词未到复习时间"

            self.lbl_rw.configure(text=msg)
            self.txt_rm.configure(state="normal")
            self.txt_rm.delete("0.0", "end")
            self.txt_rm.configure(state="disabled")
            self.btn_rev.pack_forget()
            self.review_progress_bar.set(1)
            self.lbl_review_progress.configure(text=f"已完成 {self.review_completed} 个单词")
            self.unbind_all("<space>")
            self.unbind_all("<Left>")
            self.unbind_all("<Right>")
            self.unbind_all("<Return>")
            return

        # 显示拼写卡片
        self.card.pack_forget()
        self.btn_rev.pack_forget()
        self.act_frame.pack_forget()
        self.spelling_card.pack(fill="x", pady=20, padx=20)

        self.cur_word = self.queue[0]

        # 显示释义
        meaning_text = f"{self.cur_word.get('phonetic', '')}\n\n{self.cur_word['meaning']}"
        if self.cur_word.get('example'):
            meaning_text += f"\n\n[例句] {self.cur_word['example']}"

        self.txt_spelling_meaning.configure(state="normal")
        self.txt_spelling_meaning.delete("0.0", "end")
        self.txt_spelling_meaning.insert("0.0", meaning_text)
        self.txt_spelling_meaning.configure(state="disabled")

        # 设置发音按钮
        self.btn_spelling_play.configure(command=lambda: self.play_audio(self.cur_word['word']))

        # 自动播放发音
        self.play_audio(self.cur_word['word'])

        # 聚焦输入框
        self.entry_spelling.focus_set()

        # 绑定 Enter 键到检查功能
        self.unbind_all("<Return>")
        self.bind_all("<Return>", lambda e: self.check_spelling())

    def check_spelling(self):
        """检查拼写是否正确"""
        if not self.cur_word or self.spelling_checked:
            return

        # 获取并清理输入 (忽略大小写和首尾标点)
        user_input_raw = self.entry_spelling.get().strip()
        user_input_clean = user_input_raw.lower().strip(".,;?!")

        correct_word_raw = self.cur_word['word'].strip()
        correct_word_clean = correct_word_raw.lower().strip(".,;?!")

        self.spelling_checked = True
        self.entry_spelling.configure(state="disabled")
        self.btn_check_spelling.configure(state="disabled")

        if user_input_clean == correct_word_clean:
            # 拼写正确
            self.lbl_spelling_result.configure(text="✅ 正确！", text_color="green")
            self.lbl_correct_answer.configure(text=f"单词: {correct_word_raw}", text_color="green")
            self.entry_spelling.configure(border_color="green")
            self.spelling_correct = True
        else:
            # 拼写错误
            self.lbl_spelling_result.configure(text="❌ 错误", text_color="red")
            self.lbl_correct_answer.configure(
                text=f"正确答案: {correct_word_raw}\n你的输入: {user_input_raw or '(空)'}",
                text_color="red"
            )
            self.entry_spelling.configure(border_color="red")
            self.spelling_correct = False

        # 显示下一个按钮
        self.btn_spelling_next.pack(pady=20)
        self.btn_spelling_next.focus_set() # 聚焦按钮

        # 绑定 Enter 键到下一个功能
        self.unbind_all("<Return>")
        self.bind_all("<Return>", lambda e: self.spelling_next())

    def spelling_next(self):
        """拼写模式进入下一个单词"""
        if not self.cur_word:
            return

        # 处理复习结果
        ok = getattr(self, 'spelling_correct', False)
        self.process_spelling_review(ok)

    def process_spelling_review(self, ok):
        """处理拼写复习结果"""
        if not self.cur_word:
            return

        INTERVALS = [1, 2, 4, 7, 15, 30]
        word = self.cur_word['word']

        if ok:
            stage = self.cur_word.get('stage', 0)

            if stage < len(INTERVALS):
                days = INTERVALS[stage]
                next_ts = (datetime.now() + timedelta(days=days)).timestamp()
                new_stage = stage + 1
                mastered = False
            else:
                next_ts = 0
                new_stage = stage + 1
                mastered = True
        else:
            new_stage = 0
            next_ts = 0
            mastered = False

        # 使用数据库更新复习状态
        self.db.update_review_status(word, new_stage, next_ts, mastered)
        self.reload_vocab_list()

        self.queue.pop(0)

        # 只有正确时才计入完成数
        if ok:
            self.review_completed += 1
        else:
            import random
            insert_pos = random.randint(1, len(self.queue)) if len(self.queue) > 0 else 0
            # 重新从数据库获取更新后的单词数据
            updated_word = self.db.get_word(word)
            if updated_word:
                self.queue.insert(insert_pos, updated_word)

        self.next_spelling_card()

    def create_section_header(self, parent, icon, title, color):
        """创建带颜色的分节标题"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=(20, 15))

        # 图标背景容器
        icon_bg = ctk.CTkFrame(frame, width=36, height=36, corner_radius=8, fg_color=color)
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)

        ctk.CTkLabel(icon_bg, text=icon, font=("Segoe UI Emoji", 20), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text=title, font=("Microsoft YaHei UI", 16, "bold")).pack(side="left", padx=12)

    # --- SETTINGS FRAME ---
    def create_settings_frame(self):
        self.frames["settings"] = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        # 使用原生 Canvas + Frame 实现滚动，避免 CTkScrollableFrame 性能问题
        import tkinter as tk

        # 创建容器
        scroll_container = ctk.CTkFrame(self.frames["settings"], fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

        # 创建 Canvas
        self.settings_canvas = tk.Canvas(
            scroll_container,
            bg=self._apply_appearance_mode(("gray95", "gray10")),
            highlightthickness=0,
            bd=0
        )

        # 创建滚动条
        scrollbar = ctk.CTkScrollbar(scroll_container, command=self.settings_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.settings_canvas.pack(side="left", fill="both", expand=True)
        self.settings_canvas.configure(yscrollcommand=scrollbar.set)

        # 创建内部容器 Frame
        self.settings_inner = ctk.CTkFrame(self.settings_canvas, fg_color="transparent")
        self.settings_canvas_window = self.settings_canvas.create_window(
            (0, 0),
            window=self.settings_inner,
            anchor="nw"
        )

        # 绑定事件实现平滑滚动
        def on_configure(event):
            self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox("all"))
            # 更新内部 Frame 宽度以匹配 Canvas
            self.settings_canvas.itemconfig(self.settings_canvas_window, width=event.width)

        self.settings_canvas.bind("<Configure>", on_configure)

        # 鼠标滚轮滚动 - 优化滚动步长
        def on_mousewheel(event):
            # Windows 滚轮事件
            self.settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_mousewheel(event):
            self.settings_canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(event):
            self.settings_canvas.unbind_all("<MouseWheel>")

        # 只在鼠标进入设置页面时绑定滚轮
        self.settings_canvas.bind("<Enter>", bind_mousewheel)
        self.settings_canvas.bind("<Leave>", unbind_mousewheel)

        # 使用 settings_inner 作为内容容器（替代 settings_scroll）
        settings_scroll = self.settings_inner

        # === 统计信息卡片 ===
        stats_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        stats_card.pack(fill="x", padx=15, pady=(10, 8))

        # 卡片标题
        self.create_section_header(stats_card, "📊", "学习统计", "#3B8ED0")

        # 第一行：总单词数和已掌握
        row1 = ctk.CTkFrame(stats_card, fg_color="transparent")
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

        # 第二行：今日待复习
        due_box = ctk.CTkFrame(stats_card, fg_color=("#fff3e0", "#e65100"), corner_radius=10)
        due_box.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(due_box, text="⏰ 今日待复习", font=("Microsoft YaHei UI", 12), text_color="gray").pack(pady=(10, 2))
        self.lbl_due_today = ctk.CTkLabel(due_box, text="0 个", font=("Microsoft YaHei UI", 24, "bold"))
        self.lbl_due_today.pack(pady=(0, 10))

        # === 学习热力图卡片 ===
        heatmap_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        heatmap_card.pack(fill="x", padx=15, pady=8)

        self.create_section_header(heatmap_card, "🔥", "学习热力图 (过去一年)", "#FF9800")

        # 热力图 Canvas 容器
        heatmap_container = ctk.CTkFrame(heatmap_card, fg_color="transparent")
        heatmap_container.pack(fill="x", padx=20, pady=(0, 20))

        # 使用 tk.Canvas 绘制热力图
        self.heatmap_canvas = tk.Canvas(
            heatmap_container,
            height=200, # Increased height for larger boxes
            bg=self._apply_appearance_mode(("white", "#2b2b2b")),
            highlightthickness=0,
            bd=0
        )
        self.heatmap_canvas.pack(fill="x", expand=True)

        # === 快捷键设置卡片 ===
        hotkey_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        hotkey_card.pack(fill="x", padx=15, pady=8)

        self.create_section_header(hotkey_card, "⌨️", "快捷键设置", "#607D8B")

        ctk.CTkLabel(hotkey_card, text="全局唤醒快捷键",
                    font=("Microsoft YaHei UI", 13),
                    anchor="w").pack(fill="x", padx=20, pady=(0, 8))

        hk_input_row = ctk.CTkFrame(hotkey_card, fg_color="transparent")
        hk_input_row.pack(fill="x", padx=20, pady=(0, 20))

        self.entry_hk = ctk.CTkEntry(hk_input_row, height=40, font=("Microsoft YaHei UI", 14),
                                     placeholder_text="例如: ctrl+alt+v")
        self.entry_hk.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(hk_input_row, text="💾 保存", height=40, width=100,
                     font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#4CAF50", hover_color="#45a049",
                     command=self.update_hotkey).pack(side="left")

        # === 缓存管理卡片 ===
        cache_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        cache_card.pack(fill="x", padx=15, pady=8)

        self.create_section_header(cache_card, "🗂️", "缓存管理", "#FFC107")

        cache_info_box = ctk.CTkFrame(cache_card, fg_color=("#f5f5f5", "#1e1e1e"), corner_radius=10)
        cache_info_box.pack(fill="x", padx=20, pady=(0, 10))

        cache_row = ctk.CTkFrame(cache_info_box, fg_color="transparent")
        cache_row.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(cache_row, text="🎵 音频缓存", font=("Microsoft YaHei UI", 13)).pack(side="left")
        self.lbl_cache = ctk.CTkLabel(cache_row, text="计算中...", font=("Microsoft YaHei UI", 13, "bold"))
        self.lbl_cache.pack(side="left", padx=10)

        ctk.CTkButton(cache_card, text="🗑️ 清理缓存", height=40,
                     font=("Microsoft YaHei UI", 13, "bold"),
                     fg_color="#f44336", hover_color="#da190b",
                     command=self.clear_cache).pack(fill="x", padx=20, pady=(0, 20))

        # === 外观设置卡片 ===
        appearance_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        appearance_card.pack(fill="x", padx=15, pady=8)

        self.create_section_header(appearance_card, "🎨", "外观设置", "#9C27B0")

        theme_row = ctk.CTkFrame(appearance_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(theme_row, text="主题模式",
                    font=("Microsoft YaHei UI", 13)).pack(side="left")

        self.theme_dropdown = ctk.CTkOptionMenu(
            theme_row,
            values=["浅色", "深色", "跟随系统"],
            width=120,
            height=35,
            font=("Microsoft YaHei UI", 13),
            command=self.change_theme
        )
        # 设置当前主题
        current_mode = ctk.get_appearance_mode()
        mode_map = {"Light": "浅色", "Dark": "深色", "System": "跟随系统"}
        self.theme_dropdown.set(mode_map.get(current_mode, "浅色"))
        self.theme_dropdown.pack(side="right")

        # === 捐赠支持卡片 ===
        donate_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        donate_card.pack(fill="x", padx=15, pady=8)

        self.create_section_header(donate_card, "❤️", "支持开发", "#E91E63")

        ctk.CTkLabel(donate_card,
                    text="如果这个应用对您有帮助，欢迎支持作者继续开发 💖",
                    font=("Microsoft YaHei UI", 13),
                    text_color=("gray40", "gray60"),
                    anchor="w").pack(fill="x", padx=20, pady=(0, 15))

        # 请喝咖啡按钮
        self.btn_donate = ctk.CTkButton(
            donate_card,
            text="☕ 请我喝杯咖啡",
            height=50,
            font=("Microsoft YaHei UI", 16, "bold"),
            fg_color=("#FF6B6B", "#C92A2A"),
            hover_color=("#FF5252", "#B71C1C"),
            corner_radius=12,
            command=self.toggle_donate_qr
        )
        self.btn_donate.pack(fill="x", padx=20, pady=(0, 10))

        # 二维码容器（初始隐藏）- 延迟加载图片
        self.qr_container = ctk.CTkFrame(donate_card, fg_color=("#f0f0f0", "#1e1e1e"), corner_radius=10)
        self.donate_qr_loaded = False  # 标记二维码是否已加载
        self.donate_qr_available = os.path.exists("donate_qr.png")
        self.qr_visible = False

        # === 关于信息卡片 ===
        about_card = ctk.CTkFrame(settings_scroll, fg_color=("white", "#2b2b2b"), corner_radius=15)
        about_card.pack(fill="x", padx=15, pady=(8, 15))

        self.create_section_header(about_card, "ℹ️", "关于", "#2196F3")

        ctk.CTkLabel(about_card, text="智能生词本 v3.0",
                    font=("Microsoft YaHei UI", 16, "bold"),
                    anchor="w").pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(about_card, text="基于间隔重复算法的智能单词记忆工具",
                    font=("Microsoft YaHei UI", 12),
                    text_color=("gray40", "gray60"),
                    anchor="w").pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(about_card, text="数据存储: SQLite 数据库",
                    font=("Microsoft YaHei UI", 12),
                    text_color=("gray40", "gray60"),
                    anchor="w").pack(fill="x", padx=20, pady=(2, 20))

    def refresh_settings(self):
        """刷新设置页面的所有信息"""
        # 使用数据库获取统计信息
        stats = self.db.get_statistics()

        total = stats['total']
        mastered = stats['mastered']
        due_today = stats['due_today']

        # 更新统计卡片 - 简洁的数字显示
        self.lbl_total_words.configure(text=f"{total}")

        percentage = mastered*100//total if total > 0 else 0
        self.lbl_mastered.configure(text=f"{mastered} ({percentage}%)")

        self.lbl_due_today.configure(text=f"{due_today} 个")

        # 刷新热力图
        self.draw_heatmap()

        # 快捷键
        self.entry_hk.delete(0, "end")
        self.entry_hk.insert(0, self.current_hotkey)

        # 缓存大小
        size = 0
        count = 0
        if os.path.exists(SOUNDS_DIR):
            for f in os.listdir(SOUNDS_DIR):
                fp = os.path.join(SOUNDS_DIR, f)
                if os.path.isfile(fp):
                    size += os.path.getsize(fp)
                    count += 1
        self.lbl_cache.configure(text=f"{count} 个文件 ({size/1024/1024:.1f} MB)")

    def draw_heatmap(self):
        self.heatmap_canvas.delete("all")

        # 获取数据
        data = self.db.get_review_heatmap_data()

        # 配置
        box_size = 18
        gap = 3
        margin_left = 30  # 留出左侧星期标签空间
        margin_top = 20

        # 颜色配置 (浅色模式 / 深色模式)
        # 获取实际的背景色
        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"

        # 更新 Canvas 背景色
        bg_color = "#2b2b2b" if is_dark else "white"
        self.heatmap_canvas.configure(bg=bg_color)

        if is_dark:
            colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
            text_color = "gray60"
        else:
            colors = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
            text_color = "gray50"

        # 计算日期范围 (过去 52 周)
        today = datetime.now()
        # 调整到一年前
        end_date = today
        start_date = end_date - timedelta(days=364) # 52周

        # 调整 start_date 到周日 (weekday: Mon=0, Sun=6)
        # 我们希望从周日开始绘制第一行
        # Python weekday: Mon=0...Sun=6.
        # 我们的网格: Row 0 = Sun, Row 1 = Mon ... Row 6 = Sat
        current_weekday = start_date.weekday() # 0-6
        days_to_subtract = (current_weekday + 1) % 7
        start_date -= timedelta(days=days_to_subtract)

        # 绘制
        current = start_date
        col = 0

        # 月份标签
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            count = data.get(date_str, 0)

            # 确定颜色
            if count == 0: color = colors[0]
            elif count <= 3: color = colors[1]
            elif count <= 6: color = colors[2]
            elif count <= 9: color = colors[3]
            else: color = colors[4]

            # 计算位置
            # weekday: Mon=0...Sun=6 -> 我们需要 Sun=0...Sat=6
            day_of_week = (current.weekday() + 1) % 7

            x1 = margin_left + col * (box_size + gap)
            y1 = margin_top + day_of_week * (box_size + gap)
            x2 = x1 + box_size
            y2 = y1 + box_size

            self.heatmap_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

            # 绘制月份标签 (每月第一周显示)
            if day_of_week == 0 and current.day <= 7:
                 self.heatmap_canvas.create_text(x1, margin_top - 10, text=months[current.month-1],
                                                fill=text_color, font=("Arial", 9), anchor="w")

            # 更新日期
            current += timedelta(days=1)
            if day_of_week == 6:
                col += 1

        # 绘制星期标签 (Mon, Wed, Fri) -> 对应 Row 1, 3, 5
        days_label = ["Mon", "Wed", "Fri"]
        days_idx = [1, 3, 5]

        for i, label in zip(days_idx, days_label):
            y = margin_top + i * (box_size + gap) + box_size/2
            self.heatmap_canvas.create_text(margin_left - 5, y, text=label,
                                           fill=text_color, font=("Arial", 9), anchor="e")

    def update_hotkey(self):

        new_hk = self.entry_hk.get().strip()
        if new_hk:
            self.current_hotkey = new_hk
            self.config['hotkey'] = new_hk
            save_config(self.config)
            self.setup_hotkey()
            messagebox.showinfo("成功", f"快捷键已更新为: {new_hk}")

    def change_theme(self, choice):
        """切换主题模式"""
        theme_map = {"浅色": "Light", "深色": "Dark", "跟随系统": "System"}
        mode = theme_map.get(choice, "Light")
        ctk.set_appearance_mode(mode)
        # 保存到配置
        self.config['theme'] = mode
        save_config(self.config)

        # 刷新热力图以适配新主题
        self.after(100, self.draw_heatmap)

    def clear_cache(self):
        if messagebox.askyesno("确认", "确定清空所有下载的音频文件吗？"):
            if os.path.exists(SOUNDS_DIR):
                import shutil
                shutil.rmtree(SOUNDS_DIR)
                os.makedirs(SOUNDS_DIR)
            self.refresh_settings()
            messagebox.showinfo("完成", "缓存已清理")

    def toggle_donate_qr(self):
        """切换捐赠二维码的显示/隐藏"""
        if not hasattr(self, 'donate_qr_available') or not self.donate_qr_available:
            messagebox.showinfo("提示", "二维码图片未找到")
            return

        # 延迟加载二维码图片（首次点击时加载）
        if not self.donate_qr_loaded:
            try:
                original_img = Image.open("donate_qr.png")
                img_width, img_height = original_img.size

                # 限制最大尺寸为 300x300，保持宽高比
                max_size = 300
                if img_width > max_size or img_height > max_size:
                    ratio = min(max_size / img_width, max_size / img_height)
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                else:
                    new_width = img_width
                    new_height = img_height

                self.donate_img = ctk.CTkImage(
                    light_image=original_img,
                    dark_image=original_img,
                    size=(new_width, new_height)
                )
                self.lbl_qr = ctk.CTkLabel(self.qr_container, image=self.donate_img, text="")
                self.lbl_qr.pack(padx=20, pady=(20, 10))

                self.lbl_qr_hint = ctk.CTkLabel(
                    self.qr_container,
                    text="扫码支持作者 💖",
                    font=("Microsoft YaHei UI", 13, "bold"),
                    text_color=("#4CAF50", "#66BB6A")
                )
                self.lbl_qr_hint.pack(pady=(0, 20))
                self.donate_qr_loaded = True
            except Exception as e:
                ctk.CTkLabel(
                    self.qr_container,
                    text=f"加载失败: {str(e)}",
                    font=("Microsoft YaHei UI", 11),
                    text_color="gray"
                ).pack(padx=40, pady=40)
                self.donate_qr_available = False
                return

        if self.qr_visible:
            # 隐藏二维码
            self.qr_container.pack_forget()
            self.btn_donate.configure(text="☕ 请我喝杯咖啡")
            self.qr_visible = False
        else:
            # 显示二维码
            self.qr_container.pack(fill="x", pady=(0, 10))
            self.btn_donate.configure(text="❌ 收起二维码")
            self.qr_visible = True

    def on_close(self):
        self.destroy()
        os._exit(0)


if __name__ == "__main__":
    app = VocabApp()
    app.mainloop()
