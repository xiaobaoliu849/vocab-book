import customtkinter as ctk
import tkinter as tk
import re
import threading
from datetime import datetime
from ..services.audio_service import AudioService
from ..services.word_family_service import WordFamilyService
from ..services.multi_dict_service import MultiDictService
from ..config import FONT_NORMAL
import webbrowser


def clean_word(text):
    """Clean word by removing leading/trailing punctuation and extra whitespace."""
    if not text:
        return ""
    word = text.strip()
    # Remove leading and trailing punctuation (keep internal hyphens)
    word = re.sub(r'^[^\w]+|[^\w]+$', '', word, flags=re.UNICODE)
    return word

class DetailWindow(ctk.CTkToplevel):
    def __init__(self, master, item, controller, items_list=None, current_index=0):
        super().__init__(master)
        self.item = item
        self.controller = controller
        self.items_list = items_list or [item]
        self.current_index = current_index
        self.multi_dict_frames = {}

        self.title(f"单词详情: {item['word']}")
        self.geometry("680x880") # Slightly taller for navigation

        # 设置窗口图标
        self._set_window_icon()

        self.setup_ui()
        self.load_word_data()
        
        # Remove grab_set() as it can block minimize button on some Windows environments.
        # Use focus_force to ensure it pops up but remains a standard window.
        self.after(10, self.focus_force)

    def _set_window_icon(self):
        """设置窗口图标 - 复制自主程序"""
        import os
        import sys
        
        def do_set_icon():
            try:
                from PIL import ImageTk, Image
                
                # 获取应用根目录
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
                # 候选图标路径
                candidates = [
                    (os.path.join(base_dir, 'app.ico'), 'ico'),
                    (os.path.join(os.getcwd(), 'app.ico'), 'ico'),
                ]
                
                for path, type_ in candidates:
                    if os.path.exists(path):
                        try:
                            self.iconbitmap(path)
                            print(f"DetailWindow: Success setting icon from {path}")
                            return
                        except Exception as e:
                            print(f"DetailWindow: Error setting {path}: {e}")
            except Exception as e:
                print(f"DetailWindow: Setup icon failed: {e}")
        
        # 使用延迟确保窗口完全创建
        self.after(200, do_set_icon)

    def setup_ui(self):
        self.configure(fg_color=("white", "#1e1e1e"))
        
        # --- Header Section with Navigation ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 10))

        # Navigation & Branding Row (Centered Pill Style)
        nav_container = ctk.CTkFrame(header, fg_color="transparent")
        nav_container.pack(fill="x", pady=(0, 10))
        
        # Inner centered group
        self.nav_group = ctk.CTkFrame(nav_container, fg_color="transparent")
        self.nav_group.place(relx=0.5, rely=0.5, anchor="center")
        
        # Modern Ghost Navigation Buttons
        self.btn_prev = ctk.CTkButton(
            self.nav_group, text="‹", width=34, height=34, corner_radius=17,
            fg_color="transparent", text_color=("#3B8ED0", "#64B5F6"),
            border_width=1, border_color=("#3B8ED0", "#64B5F6"),
            hover_color=("#E3F2FD", "#1a3a5a"), 
            font=("Arial", 22, "bold"),
            command=self.prev_word
        )
        self.btn_prev.pack(side="left", padx=5)

        # Page Indicator (e.g., 5 / 120) - Modern font
        self.lbl_nav_info = ctk.CTkLabel(
            self.nav_group, text="", 
            font=("Segoe UI Semibold", 13), 
            text_color=("#555555", "#aaaaaa")
        )
        self.lbl_nav_info.pack(side="left", padx=15)

        self.btn_next = ctk.CTkButton(
            self.nav_group, text="›", width=34, height=34, corner_radius=17,
            fg_color="transparent", text_color=("#3B8ED0", "#64B5F6"),
            border_width=1, border_color=("#3B8ED0", "#64B5F6"),
            hover_color=("#E3F2FD", "#1a3a5a"), 
            font=("Arial", 22, "bold"),
            command=self.next_word
        )
        self.btn_next.pack(side="left", padx=5)

        # Ensure container has enough height for the localized group
        nav_container.configure(height=45)
        nav_container.pack_propagate(False)

        # Main Info area (Centered word)
        info_container = ctk.CTkFrame(header, fg_color="transparent")
        info_container.pack(fill="x", pady=(15, 0))

        self.word_label = ctk.CTkLabel(
            info_container, text="", 
            font=("Microsoft YaHei UI", 42, "bold"), 
            text_color=("#1a1a1a", "#ffffff"),
            anchor="w"
        )
        self.word_label.pack(side="left")

        self.phonetic_label = ctk.CTkLabel(
            info_container, text="", 
            font=("Arial", 20), 
            text_color=("#3B8ED0", "#64B5F6")
        )
        self.phonetic_label.pack(side="left", padx=20)

        # 播放按钮放在同一行的右侧
        self.btn_play = ctk.CTkButton(
            info_container, text="🔊", width=44, height=44, corner_radius=22, 
            font=("Arial", 20), fg_color=("#4CAF50", "#2E7D32"), 
            hover_color=("#388E3C", "#1B5E20"), command=self.play_audio
        )
        self.btn_play.pack(side="right", padx=(0, 10))

        # --- Main Scrollable Content ---
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # Static placeholder for dynamic content to fix order
        self.content_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.content_container.pack(fill="x")

        # Fixed position containers
        self.multi_dict_section = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.multi_dict_section.pack(fill="x")

        self.word_family_section = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.word_family_section.pack(fill="x")

        self.stats_section = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.stats_section.pack(fill="x")

        self.create_context_menu()

    def load_word_data(self):
        """Load or refresh the data for the current index."""
        self.item = self.items_list[self.current_index]
        self.title(f"单词详情: {self.item['word']}")
        
        # 1. Update Header
        self.word_label.configure(text=self.item['word'])
        phonetic = self.item.get('phonetic', '')
        self.phonetic_label.configure(text=f"/{phonetic}/" if phonetic else "")
        
        # Update Nav context info
        self.lbl_nav_info.configure(text=f"{self.current_index + 1}  /  {len(self.items_list)}")

        # Update Nav buttons state (Disabled instead of packing/unpacking for stability)
        if self.current_index > 0:
            self.btn_prev.configure(state="normal", border_color=("#3B8ED0", "#64B5F6"))
        else:
            self.btn_prev.configure(state="disabled", border_color="gray80")

        if self.current_index < len(self.items_list) - 1:
            self.btn_next.configure(state="normal", border_color=("#3B8ED0", "#64B5F6"))
        else:
            self.btn_next.configure(state="disabled", border_color="gray80")

        # 2. Clear Containers
        for widget in self.content_container.winfo_children(): widget.destroy()
        for widget in self.multi_dict_section.winfo_children(): widget.destroy()
        for widget in self.word_family_section.winfo_children(): widget.destroy()
        for widget in self.stats_section.winfo_children(): widget.destroy()

        # 3. Populate Primary Content
        self.create_content_card(self.content_container, "📖 核心释义", self.item.get('meaning', ''), accent_color="#3B8ED0")
        if self.item.get('example'):
            self.create_content_card(self.content_container, "📝 经典例句", self.item.get('example', ''), accent_color="#FF9800")

        if self.item.get('roots') or self.item.get('synonyms'):
            extra_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
            extra_container.pack(fill="x", pady=5)
            extra_container.grid_columnconfigure((0, 1), weight=1)
            if self.item.get('roots'):
                self.create_small_card(extra_container, "🌱 词根", self.item.get('roots', ''), 0, "#4CAF50")
            if self.item.get('synonyms'):
                self.create_small_card(extra_container, "🔗 同义", self.item.get('synonyms', ''), 1, "#9C27B0")

        if self.item.get('context_en'):
            ctx_text = f"{self.item['context_en']}\n\n{self.item.get('context_cn','')}".strip()
            self.create_content_card(self.content_container, "✍️ 来源语境", ctx_text, accent_color="#9C27B0")

        # 4. Global Action Footer (Re-packed at bottom if needed, but here we use a container)
        # Note: Footer is packed to window bottom in __init__? Actually it's in setup_ui.
        # Fixed footer below the scrollbox
        if not hasattr(self, 'footer'):
            self.setup_footer()

        # 5. Populate Async Sections (Containers are already in fixed order)
        self.add_section_header(self.multi_dict_section, "📚 聚合词典详情")
        self.multi_dict_container = ctk.CTkFrame(self.multi_dict_section, fg_color="transparent")
        self.multi_dict_container.pack(fill="x", pady=(5, 10))
        self.multi_dict_loading = ctk.CTkLabel(self.multi_dict_container, text="⏳ 检索增强中...", font=("Microsoft YaHei UI", 12), text_color="gray")
        self.multi_dict_loading.pack(pady=10)

        self.setup_word_family_section(self.word_family_section)
        self.setup_stats_dashboard(self.stats_section)

        # 6. Kick off Background Tasks
        self.multi_dict_frames = {}
        self.load_multi_dict_results()

    def prev_word(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_word_data()
            self._scroll_to_top()

    def next_word(self):
        if self.current_index < len(self.items_list) - 1:
            self.current_index += 1
            self.load_word_data()
            self._scroll_to_top()

    def _scroll_to_top(self):
        # Access internal canvas for scrolling
        try:
            self.scroll._parent_canvas.yview_moveto(0)
        except:
            pass

    def setup_footer(self):
        self.footer = ctk.CTkFrame(self, fg_color="transparent", height=70)
        self.footer.pack(fill="x", side="bottom", padx=30, pady=15)
        self.footer.pack_propagate(False)

        ctk.CTkButton(
            self.footer, text="✏️ 编辑单词", height=40, corner_radius=20,
            fg_color=("#3B8ED0", "#1f538d"), font=("Microsoft YaHei UI", 13, "bold"),
            command=self.edit_word
        ).pack(side="left", expand=True, padx=8)

        ctk.CTkButton(
            self.footer, text="🗑️ 彻底删除", height=40, corner_radius=20,
            fg_color="#F44336", hover_color="#D32F2F", font=("Microsoft YaHei UI", 13, "bold"),
            command=self.delete_word
        ).pack(side="left", expand=True, padx=8)

    def create_selectable_text(self, parent, text, font_size, width_chars, color=None):
        """使用 CTkLabel 显示文本，简单稳定"""
        text = text.strip()
        text = re.sub(r'\.([a-zA-Z])', r'. \1', text)
        
        if not text:
            text = " "
        
        # 使用 CTkLabel，简单稳定
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=("Microsoft YaHei UI", font_size),
            text_color=color if color else ("gray20", "gray80"),
            anchor="nw",
            justify="left",
            wraplength=480  # 适合详情页宽度
        )
        
        return label

    def create_content_card(self, parent, title, content, accent_color):
        """紧凑卡片布局"""
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=10, border_width=1, border_color=("gray90", "gray30"))
        card.pack(fill="x", pady=4)
        
        # 简单的内部布局：左边装饰条 + 右边内容
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)
        
        # 使用 grid 布局确保装饰条不会拉伸
        inner.grid_columnconfigure(1, weight=1)
        
        # 装饰条 - 固定高度，不用 fill
        accent = ctk.CTkFrame(inner, width=4, height=50, fg_color=accent_color, corner_radius=2)
        accent.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 10))
        
        # 标题
        ctk.CTkLabel(inner, text=title, font=("Microsoft YaHei UI", 11, "bold"), text_color="gray50", anchor="w").grid(row=0, column=1, sticky="w")
        
        # 内容
        content_label = self.create_selectable_text(inner, content, 13, 50)
        content_label.grid(row=1, column=1, sticky="w", pady=(4, 0))

    def create_small_card(self, parent, title, content, column, color):
        card = ctk.CTkFrame(parent, fg_color=("white", "#2b2b2b"), corner_radius=12, border_width=1, border_color=("gray90", "gray30"))
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8, 2))
        
        ctk.CTkLabel(header_frame, text=title, font=("Microsoft YaHei UI", 11, "bold"), text_color=color, anchor="w").pack(side="left")
        
        self.create_selectable_text(card, content, 12, 24).pack(fill="x", padx=10, pady=(0, 8))

    def setup_stats_dashboard(self, parent):
        self.add_section_header(parent, "📊 复习数据面板")
        dash = ctk.CTkFrame(parent, fg_color="transparent")
        dash.pack(fill="x", pady=5)
        dash.grid_columnconfigure((0, 1), weight=1)

        def create_stat_tile(row, col, label, value, icon):
            tile = ctk.CTkFrame(dash, fg_color=("gray95", "#242424"), corner_radius=10, height=50)
            tile.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
            tile.grid_propagate(False)
            
            icon_lbl = ctk.CTkLabel(tile, text=icon, font=("Arial", 16))
            icon_lbl.pack(side="left", padx=(10, 5))
            
            txt_container = ctk.CTkFrame(tile, fg_color="transparent")
            txt_container.pack(side="left", fill="y", pady=5)
            
            ctk.CTkLabel(txt_container, text=label, font=("Microsoft YaHei UI", 10), text_color="gray50").pack(anchor="w")
            ctk.CTkLabel(txt_container, text=value, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w")

        r_count = str(self.item.get('review_count', 0))
        status = '已掌握' if self.item.get('mastered') else '学习中'
        next_rev = self.format_next_review(self.item.get('next_review_time', 0))
        interval = f"{self.item.get('interval', 0)} 天"

        create_stat_tile(0, 0, "回想次数", r_count, "🔄")
        create_stat_tile(0, 1, "掌握进度", status, "🏆")
        create_stat_tile(1, 0, "复习安排", next_rev, "📅")
        create_stat_tile(1, 1, "记忆间隔", interval, "⏳")

    def add_section_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Microsoft YaHei UI", 14, "bold"), text_color="gray50", anchor="w").pack(fill="x", pady=(5, 0))

    def setup_word_family_section(self, parent):
        """设置派生词群组区域"""
        # Capture the word for which we are loading data to prevent race conditions
        current_word = self.item['word']
        
        def load_word_families():
            try:
                word_family_data = WordFamilyService.get_derivatives(
                    current_word,
                    self.controller.db
                )
                # Check if the word still matches (user might have navigated)
                if self.winfo_exists() and self.item['word'] == current_word:
                    self.after(0, lambda: self.display_word_families(parent, word_family_data))
            except Exception as e:
                print(f"Error loading word families: {e}")

        threading.Thread(target=load_word_families, daemon=True).start()

    def display_word_families(self, parent, data):
        """显示派生词群组"""
        families = data.get('families', [])
        if not families:
            return

        self.add_section_header(parent, "🌳 派生词群组")

        for family in families:
            root = family.get('root', '')
            meaning = family.get('meaning', '')
            in_vocab = family.get('in_vocab', [])
            not_in_vocab = family.get('not_in_vocab', [])

            # 词根标题框
            root_frame = ctk.CTkFrame(parent, fg_color=("#E8F5E9", "#1B5E20"), corner_radius=12)
            root_frame.pack(fill="x", pady=(12, 5))

            root_label = ctk.CTkLabel(
                root_frame,
                text=f"🌳 词根: {root}- ({meaning})",
                font=("Microsoft YaHei UI", 12, "bold"),
                text_color=("#1B5E20", "#A5D6A7")
            )
            root_label.pack(anchor="w", padx=15, pady=10)

            # 派生词容器
            words_frame = ctk.CTkFrame(parent, fg_color="transparent")
            words_frame.pack(fill="x", padx=5, pady=(0, 10))

            # 已在词库的派生词
            if in_vocab:
                in_vocab_frame = ctk.CTkFrame(words_frame, fg_color="transparent")
                in_vocab_frame.pack(fill="x", pady=2)

                ctk.CTkLabel(
                    in_vocab_frame,
                    text="📚 已在词库:",
                    font=("Microsoft YaHei UI", 11),
                    text_color="gray60"
                ).pack(side="left", padx=(0, 5))

                for word in in_vocab[:8]:  # 限制显示数量
                    word_btn = ctk.CTkButton(
                        in_vocab_frame,
                        text=f"✓ {word}",
                        font=("Microsoft YaHei UI", 11),
                        fg_color=("#C8E6C9", "#2E7D32"),
                        text_color=("#1B5E20", "#E8F5E9"),
                        hover_color=("#A5D6A7", "#388E3C"),
                        height=26,
                        corner_radius=13,
                        command=lambda w=word: self.view_word(w)
                    )
                    word_btn.pack(side="left", padx=2)

            # 未在词库的派生词（可点击添加）
            if not_in_vocab:
                not_in_vocab_frame = ctk.CTkFrame(words_frame, fg_color="transparent")
                not_in_vocab_frame.pack(fill="x", pady=2)

                ctk.CTkLabel(
                    not_in_vocab_frame,
                    text="💡 推荐添加:",
                    font=("Microsoft YaHei UI", 11),
                    text_color="gray60"
                ).pack(side="left", padx=(0, 5))

                for word in not_in_vocab[:6]:  # 限制显示数量
                    word_btn = ctk.CTkButton(
                        not_in_vocab_frame,
                        text=f"+ {word}",
                        font=("Microsoft YaHei UI", 11),
                        fg_color=("#FFF3E0", "#E65100"),
                        text_color=("#E65100", "#FFE0B2"),
                        hover_color=("#FFE0B2", "#F57C00"),
                        height=26,
                        corner_radius=13,
                        command=lambda w=word: self.quick_add_word(w)
                    )
                    word_btn.pack(side="left", padx=2)

    def view_word(self, word):
        """查看词库中已有的单词"""
        word_data = self.controller.db.get_word(word)
        if word_data:
            # Check if it's already in our current navigation list
            for i, itm in enumerate(self.items_list):
                if itm['word'].lower() == word.lower():
                    self.current_index = i
                    self.load_word_data()
                    self._scroll_to_top()
                    return
            
            # If not in list, add it to the list right after current word and navigate to it
            self.items_list.insert(self.current_index + 1, word_data)
            self.current_index += 1
            self.load_word_data()
            self._scroll_to_top()

    def quick_add_word(self, word):
        """快速添加派生词到词库"""
        # 跳转到添加界面并自动搜索
        self.controller.show_frame("add")
        if "add" in self.controller.frames:
            add_view = self.controller.frames["add"]
            add_view.entry_word.delete(0, "end")
            add_view.entry_word.insert(0, word)
            add_view.after(100, add_view.start_search)
        self.destroy()

    def format_next_review(self, ts):
        if ts == 0: return "新单词"
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")

    def play_audio(self):
        if not AudioService.is_available(): return

        # Clean word before playing
        word_to_play = clean_word(self.item['word'])
        if not word_to_play:
            return

        self.btn_play.configure(text="⏳", fg_color="orange")
        def _play():
            try:
                AudioService.play_word(word_to_play)
                self.after(0, lambda: self.btn_play.configure(text="🔊", fg_color="green"))
            except Exception:
                self.after(0, lambda: self.btn_play.configure(text="🔊", fg_color="gray"))
        threading.Thread(target=_play, daemon=True).start()

    def edit_word(self):
        self.controller.show_frame("add")
        if "add" in self.controller.frames:
            self.controller.frames["add"].load_word(self.item)
        self.destroy()

    def create_context_menu(self):
        # Configure menu font
        menu_font = ("Microsoft YaHei UI", 12)

        self.context_menu = tk.Menu(self, tearoff=0, font=menu_font)
        self.context_menu.add_command(label="复制 (Copy)", command=self.on_copy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="查词 (Look up)", command=self.on_app_lookup)
        self.current_text_widget = None

    def bind_context_menu(self, widget):
        widget.bind("<Button-3>", lambda e, w=widget: self.show_context_menu(e, w))
        widget.bind("<Button-2>", lambda e, w=widget: self.show_context_menu(e, w)) # macOS

    def show_context_menu(self, event, widget):
        self.current_text_widget = widget
        # Only show if text is selected
        if self.get_selected_text():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def get_selected_text(self):
        if not self.current_text_widget: return ""
        try:
            return self.current_text_widget.selection_get()
        except tk.TclError:
            return ""

    def on_copy(self):
        text = self.get_selected_text()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()

    def on_app_lookup(self):
        text = self.get_selected_text()
        if text:
            # Clean up text (remove punctuation)
            word = clean_word(text)
            if not word: return

            # Switch to Add view and search
            self.controller.show_frame("add")
            if "add" in self.controller.frames:
                add_view = self.controller.frames["add"]
                add_view.entry_word.delete(0, "end")
                add_view.entry_word.insert(0, word)
                # Use after to allow UI to switch before starting search
                # allow_network=False: 已有单词直接显示，不再增强搜索
                add_view.after(100, lambda: add_view.start_search(allow_network=False))

            # Close detail window
            self.destroy()

    def delete_word(self):
        from tkinter import messagebox
        if messagebox.askyesno("确认", "确定删除该单词吗？"):
            self.controller.db.delete_word(self.item['word'])
            self.controller.reload_vocab_list()
            if "list" in self.controller.frames:
                self.controller.frames["list"].refresh_list()
            self.destroy()

    def load_multi_dict_results(self):
        """在后台线程中查询多词典"""
        current_word = self.item['word']
        
        def query_dicts():
            try:
                # 获取启用的词典
                config = self.controller.config
                dict_sources = config.get("dict_sources", {
                    "youdao": True,
                    "bing": True,
                    "freedict": True
                })

                enabled = [k for k, v in dict_sources.items() if v and k != "youdao"]

                if not enabled:
                    self.after(0, self.hide_multi_dict_loading)
                    return

                # 查询 Bing 和 Free Dictionary
                results = {}

                if "bing" in enabled:
                    bing_result = MultiDictService.search_bing(current_word)
                    if bing_result:
                        results["bing"] = bing_result

                if "freedict" in enabled:
                    free_result = MultiDictService.search_free_dict(current_word)
                    if free_result:
                        results["freedict"] = free_result

                # 更新UI前检查窗口是否存在且单词依然匹配
                if self.winfo_exists() and self.item['word'] == current_word:
                    self.after(0, lambda: self.display_multi_dict_results(results))

            except Exception as e:
                print(f"Multi-dict query error: {e}")
                if self.winfo_exists() and self.item['word'] == current_word:
                    self.after(0, self.hide_multi_dict_loading)

        threading.Thread(target=query_dicts, daemon=True).start()

    def hide_multi_dict_loading(self):
        """隐藏加载提示"""
        if hasattr(self, 'multi_dict_loading') and self.multi_dict_loading.winfo_exists():
            self.multi_dict_loading.configure(text="暂无其他词典结果")

    def display_multi_dict_results(self, results):
        """显示多词典查询结果"""
        if not hasattr(self, 'multi_dict_loading') or not self.multi_dict_loading.winfo_exists():
            return

        # 隐藏加载提示
        self.multi_dict_loading.pack_forget()

        if not results:
            no_result_label = ctk.CTkLabel(
                self.multi_dict_container,
                text="未找到其他词典结果",
                font=("Microsoft YaHei UI", 12),
                text_color="gray"
            )
            no_result_label.pack(pady=10)
            return

        # 显示每个词典的结果
        for source, data in results.items():
            self.create_dict_block(source, data)

    def create_dict_block(self, source, data):
        """创建现代化的可折叠词典区块"""
        source_name = data.get('source_name', source)

        # 词典颜色配置 (Enhanced contrast for modern theme)
        colors = {
            "bing": {"bg": ("#E3F2FD", "#102a43"), "header": ("#0062cc", "#64B5F6"), "icon": "🔷"},
            "freedict": {"bg": ("#F3E5F5", "#2a1535"), "header": ("#7B1FA2", "#CE93D8"), "icon": "⚛️"},
            "youdao": {"bg": ("#E8F5E9", "#0e2f10"), "header": ("#2E7D32", "#81C784"), "icon": "🍏"},
        }
        color = colors.get(source, {"bg": ("#F5F5F5", "#242424"), "header": ("#757575", "#BDBDBD"), "icon": "📁"})

        # 外层容器
        block = ctk.CTkFrame(
            self.multi_dict_container,
            fg_color=color["bg"],
            corner_radius=12,
            border_width=1,
            border_color=("gray90", "gray20")
        )
        block.pack(fill="x", pady=6)

        # 头部（可点击折叠）
        header = ctk.CTkFrame(block, fg_color="transparent", cursor="hand2", height=44)
        header.pack(fill="x", padx=12, pady=5)
        header.pack_propagate(False)

        # 展开/折叠指示
        expand_label = ctk.CTkLabel(
            header, text="▼", font=("Arial", 14), text_color=color["header"]
        )
        expand_label.pack(side="left", padx=(5, 10))

        # 词典名称
        ctk.CTkLabel(
            header,
            text=f"{color['icon']} {source_name}",
            font=("Microsoft YaHei UI", 13, "bold"),
            text_color=color["header"]
        ).pack(side="left")

        # 音标覆盖项
        if data.get('phonetic'):
            ctk.CTkLabel(
                header, text=f"/{data['phonetic']}/", 
                font=("Arial", 11), text_color="gray"
            ).pack(side="left", padx=15)

        # 内容区域
        content_frame = ctk.CTkFrame(block, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=(0, 15))

        # 释义区域 (Selectable Textbox with hidden scrollbar)
        if data.get('meaning'):
            m_text = data['meaning'].strip()
            self.create_selectable_text(content_frame, m_text, 12, 42).pack(fill="x", pady=5, padx=2)

        # 例句 (Selectable Textbox)
        if data.get('example'):
            ex_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            ex_frame.pack(fill="x", pady=4)
            
            ctk.CTkLabel(
                ex_frame, text="💬 典型用例:", font=("Microsoft YaHei UI", 11, "bold"), 
                text_color="gray50"
            ).pack(anchor="w")
            
            ex_text = data['example'].strip()
            self.create_selectable_text(ex_frame, ex_text, 12, 48).pack(fill="x", padx=10, pady=2)

        # 其他元数据 (Selectable)
        meta_parts = []
        if data.get('forms'): meta_parts.append(f"形态: {data['forms']}")
        if data.get('collocations'): meta_parts.append(f"搭配: {data['collocations']}")
        if data.get('synonyms'): meta_parts.append(f"近义: {data['synonyms']}")
        
        if meta_parts:
            meta_text = "  •  ".join(meta_parts)
            self.create_selectable_text(content_frame, meta_text, 11, 55, color="gray60").pack(fill="x", pady=(5, 0), padx=5)

        # 存储引用
        self.multi_dict_frames[source] = {
            "block": block,
            "content": content_frame,
            "expand_label": expand_label,
            "expanded": True
        }

        # 绑定点击折叠事件
        def toggle_block(e, src=source):
            self.toggle_dict_block(src)

        header.bind("<Button-1>", toggle_block)
        for child in header.winfo_children():
            child.bind("<Button-1>", toggle_block)

    def toggle_dict_block(self, source):
        """切换词典区块的展开/折叠状态"""
        if source not in self.multi_dict_frames:
            return

        frame_data = self.multi_dict_frames[source]
        content = frame_data["content"]
        expand_label = frame_data["expand_label"]

        if frame_data["expanded"]:
            content.pack_forget()
            expand_label.configure(text="▶")
            frame_data["expanded"] = False
        else:
            content.pack(fill="x", padx=15, pady=(0, 10))
            expand_label.configure(text="▼")
            frame_data["expanded"] = True
