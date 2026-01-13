import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime
from ..services.audio_service import AudioService
from ..services.word_family_service import WordFamilyService
from ..services.multi_dict_service import MultiDictService
from ..config import FONT_NORMAL
import webbrowser

class DetailWindow(ctk.CTkToplevel):
    def __init__(self, master, item, controller):
        super().__init__(master)
        self.item = item
        self.controller = controller
        self.multi_dict_frames = {}  # 存储各词典的可折叠区块

        self.title(f"单词详情: {item['word']}")
        self.geometry("650x800")

        self.setup_ui()
        self.grab_set()

        # 在后台查询其他词典
        self.load_multi_dict_results()

    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        # Left side: Word and Phonetic
        word_info = ctk.CTkFrame(header, fg_color="transparent")
        word_info.pack(side="left", fill="y")

        ctk.CTkLabel(word_info, text=self.item['word'], font=("Microsoft YaHei UI", 28, "bold")).pack(side="left")

        phonetic = self.item.get('phonetic', '')
        if phonetic:
            ctk.CTkLabel(word_info, text=f"  {phonetic}", font=("Microsoft YaHei UI", 16), text_color="gray").pack(side="left", padx=10)

        # Right side: Play Button (Priority)
        self.btn_play = ctk.CTkButton(header, text="🔊", width=45, height=35, font=("Arial", 18), fg_color="green", command=self.play_audio)
        self.btn_play.pack(side="right", padx=(10, 0))

        # Tags (Optional, in the middle/left)
        tags = self.item.get('tags', '')
        if tags:
            # If tags are too long, we might want to truncate or wrap
            display_tags = tags[:20] + "..." if len(tags) > 20 else tags
            tag_frame = ctk.CTkFrame(header, fg_color=("#E3F2FD", "#1A237E"), corner_radius=6)
            tag_frame.pack(side="right", padx=10)
            ctk.CTkLabel(tag_frame, text=display_tags, font=("Microsoft YaHei UI", 11, "bold"), text_color=("#1976D2", "#BBDEFB")).pack(padx=8, pady=2)

        # Source context badge (Below word info if present)
        source_cn = self.item.get('context_cn', '')
        if source_cn:
            # Handle the long source context visible in the screenshot
            source_frame = ctk.CTkFrame(self, fg_color=("#E3F2FD", "#1A237E"), corner_radius=4)
            source_frame.pack(fill="x", padx=20, pady=(0, 10))

            # Use a label that can wrap or be truncated
            short_source = source_cn
            if len(short_source) > 60:
                short_source = short_source[:60] + "..."

            ctk.CTkLabel(source_frame, text=f"来源: {short_source}", font=("Microsoft YaHei UI", 12),
                        text_color=("#1976D2", "#64B5F6"), wraplength=580, justify="left").pack(padx=10, pady=5, anchor="w")

        # Context Menu
        self.create_context_menu()

        # Info
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.add_section_header(scroll, "📖 释义")
        txt_meaning = ctk.CTkTextbox(scroll, height=100, font=FONT_NORMAL)
        txt_meaning.pack(fill="x", pady=(5, 15))
        txt_meaning.insert("0.0", self.item.get('meaning', ''))
        txt_meaning.configure(state="disabled")
        self.bind_context_menu(txt_meaning)

        self.add_section_header(scroll, "📝 例句")
        txt_example = ctk.CTkTextbox(scroll, height=100, font=FONT_NORMAL)
        txt_example.pack(fill="x", pady=(5, 15))
        txt_example.insert("0.0", self.item.get('example', ''))
        txt_example.configure(state="disabled")
        self.bind_context_menu(txt_example)

        if self.item.get('roots'):
            self.add_section_header(scroll, "🌱 词根词缀")
            txt_roots = ctk.CTkTextbox(scroll, height=60, font=FONT_NORMAL)
            txt_roots.pack(fill="x", pady=(5, 15))
            txt_roots.insert("0.0", self.item.get('roots', ''))
            txt_roots.configure(state="disabled")
            self.bind_context_menu(txt_roots)

        if self.item.get('synonyms'):
            self.add_section_header(scroll, "🔗 同近义词")
            txt_syn = ctk.CTkTextbox(scroll, height=60, font=FONT_NORMAL)
            txt_syn.pack(fill="x", pady=(5, 15))
            txt_syn.insert("0.0", self.item.get('synonyms', ''))
            txt_syn.configure(state="disabled")
            self.bind_context_menu(txt_syn)

        # 多词典聚合区域
        self.add_section_header(scroll, "📚 多词典释义")
        self.multi_dict_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self.multi_dict_container.pack(fill="x", pady=(5, 15))

        # 加载提示
        self.multi_dict_loading = ctk.CTkLabel(
            self.multi_dict_container,
            text="⏳ 正在查询其他词典...",
            font=("Microsoft YaHei UI", 12),
            text_color="gray"
        )
        self.multi_dict_loading.pack(pady=10)

        if self.item.get('context_en'):
            self.add_section_header(scroll, "✍️ 来源语境")
            ctx_text = f"{self.item['context_en']}\n{self.item.get('context_cn','')}"
            txt_ctx = ctk.CTkTextbox(scroll, height=100, font=FONT_NORMAL)
            txt_ctx.pack(fill="x", pady=(5, 15))
            txt_ctx.insert("0.0", ctx_text)
            txt_ctx.configure(state="disabled")
            self.bind_context_menu(txt_ctx)

        # Word Family Section (派生词群组)
        self.setup_word_family_section(scroll)

        # Review Stats
        self.add_section_header(scroll, "📊 复习数据")
        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=5)

        stats = [
            f"复习次数: {self.item.get('review_count', 0)}",
            f"掌握状态: {'✅ 已掌握' if self.item.get('mastered') else '📚 学习中'}",
            f"下次复习: {self.format_next_review(self.item.get('next_review_time', 0))}",
            f"SM-2 难度 (Easiness): {self.item.get('easiness', 2.5):.2f}",
            f"当前间隔: {self.item.get('interval', 0)} 天"
        ]

        for s in stats:
            ctk.CTkLabel(stats_frame, text=f"• {s}", font=("Microsoft YaHei UI", 13), anchor="w").pack(fill="x", padx=10)

        # Actions
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(action_frame, text="✏️ 编辑 (在主界面)", fg_color="#3B8ED0", command=self.edit_word).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(action_frame, text="🗑️ 删除", fg_color="red", command=self.delete_word).pack(side="left", expand=True, padx=5)

    def add_section_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Microsoft YaHei UI", 14, "bold"), text_color="gray50", anchor="w").pack(fill="x", pady=(5, 0))

    def setup_word_family_section(self, parent):
        """设置派生词群组区域"""
        # 在后台线程中获取派生词信息
        def load_word_families():
            try:
                word_family_data = WordFamilyService.get_derivatives(
                    self.item['word'],
                    self.controller.db
                )
                # 更新UI需要在主线程
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
            root_frame = ctk.CTkFrame(parent, fg_color=("#E8F5E9", "#1B5E20"), corner_radius=8)
            root_frame.pack(fill="x", pady=(8, 5), padx=5)

            root_label = ctk.CTkLabel(
                root_frame,
                text=f"词根: {root}- ({meaning})",
                font=("Microsoft YaHei UI", 13, "bold"),
                text_color=("#1B5E20", "#A5D6A7")
            )
            root_label.pack(anchor="w", padx=10, pady=8)

            # 派生词容器
            words_frame = ctk.CTkFrame(parent, fg_color="transparent")
            words_frame.pack(fill="x", padx=10, pady=(0, 10))

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
            # 关闭当前窗口，打开新的详情窗口
            self.destroy()
            DetailWindow(self.master, word_data, self.controller)

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

        self.btn_play.configure(text="⏳", fg_color="orange")
        def _play():
            try:
                AudioService.play_word(self.item['word'])
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
            # Clean up text
            word = text.strip()
            if not word: return

            # Switch to Add view and search
            self.controller.show_frame("add")
            if "add" in self.controller.frames:
                add_view = self.controller.frames["add"]
                add_view.entry_word.delete(0, "end")
                add_view.entry_word.insert(0, word)
                # Use after to allow UI to switch before starting search
                add_view.after(100, add_view.start_search)

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
                    bing_result = MultiDictService.search_bing(self.item['word'])
                    if bing_result:
                        results["bing"] = bing_result

                if "freedict" in enabled:
                    free_result = MultiDictService.search_free_dict(self.item['word'])
                    if free_result:
                        results["freedict"] = free_result

                # 更新UI
                self.after(0, lambda: self.display_multi_dict_results(results))

            except Exception as e:
                print(f"Multi-dict query error: {e}")
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
        """创建可折叠的词典区块"""
        source_name = data.get('source_name', source)

        # 词典颜色配置
        colors = {
            "bing": {"bg": ("#E3F2FD", "#0D47A1"), "header": ("#1976D2", "#64B5F6"), "icon": "🔷"},
            "freedict": {"bg": ("#F3E5F5", "#4A148C"), "header": ("#7B1FA2", "#CE93D8"), "icon": "📖"},
            "youdao": {"bg": ("#E8F5E9", "#1B5E20"), "header": ("#388E3C", "#81C784"), "icon": "📗"},
        }
        color = colors.get(source, {"bg": ("#F5F5F5", "#424242"), "header": ("#757575", "#BDBDBD"), "icon": "📚"})

        # 外层容器
        block = ctk.CTkFrame(
            self.multi_dict_container,
            fg_color=color["bg"],
            corner_radius=10
        )
        block.pack(fill="x", pady=5)

        # 头部（可点击折叠）
        header = ctk.CTkFrame(block, fg_color="transparent", cursor="hand2")
        header.pack(fill="x", padx=10, pady=(10, 5))

        # 展开/折叠指示
        expand_label = ctk.CTkLabel(
            header,
            text="▼",
            font=("Microsoft YaHei UI", 12),
            text_color=color["header"]
        )
        expand_label.pack(side="left", padx=(0, 5))

        # 词典名称
        ctk.CTkLabel(
            header,
            text=f"{color['icon']} {source_name}",
            font=("Microsoft YaHei UI", 13, "bold"),
            text_color=color["header"]
        ).pack(side="left")

        # 音标（如果有）
        if data.get('phonetic'):
            ctk.CTkLabel(
                header,
                text=f"  {data['phonetic']}",
                font=("Microsoft YaHei UI", 11),
                text_color="gray"
            ).pack(side="left", padx=10)

        # 内容区域
        content_frame = ctk.CTkFrame(block, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=(0, 10))

        # 释义
        if data.get('meaning'):
            meaning_box = ctk.CTkTextbox(
                content_frame,
                height=80,
                font=("Microsoft YaHei UI", 12),
                fg_color=("white", "#1E1E1E"),
                corner_radius=5
            )
            meaning_box.pack(fill="x", pady=(5, 5))
            meaning_box.insert("0.0", data['meaning'])
            meaning_box.configure(state="disabled")
            self.bind_context_menu(meaning_box)

        # 词形变化（Bing特有）
        if data.get('forms'):
            forms_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            forms_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(
                forms_frame,
                text="📐 词形:",
                font=("Microsoft YaHei UI", 11),
                text_color="gray60"
            ).pack(side="left")
            ctk.CTkLabel(
                forms_frame,
                text=data['forms'],
                font=("Microsoft YaHei UI", 11),
                wraplength=500
            ).pack(side="left", padx=5)

        # 例句
        if data.get('example'):
            example_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            example_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(
                example_frame,
                text="💬 例句:",
                font=("Microsoft YaHei UI", 11),
                text_color="gray60"
            ).pack(anchor="w")
            example_label = ctk.CTkLabel(
                example_frame,
                text=data['example'],
                font=("Microsoft YaHei UI", 11),
                wraplength=550,
                justify="left"
            )
            example_label.pack(anchor="w", padx=10)

        # 搭配短语（Bing特有）
        if data.get('collocations'):
            coll_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            coll_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(
                coll_frame,
                text="🔗 常用搭配:",
                font=("Microsoft YaHei UI", 11),
                text_color="gray60"
            ).pack(side="left")
            ctk.CTkLabel(
                coll_frame,
                text=data['collocations'],
                font=("Microsoft YaHei UI", 11),
                wraplength=450
            ).pack(side="left", padx=5)

        # 同义词
        if data.get('synonyms'):
            syn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            syn_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(
                syn_frame,
                text="🔀 同义词:",
                font=("Microsoft YaHei UI", 11),
                text_color="gray60"
            ).pack(side="left")
            ctk.CTkLabel(
                syn_frame,
                text=data['synonyms'],
                font=("Microsoft YaHei UI", 11),
                wraplength=450
            ).pack(side="left", padx=5)

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
