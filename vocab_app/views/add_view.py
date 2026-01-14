import customtkinter as ctk
import tkinter as tk
import threading
from tkinter import messagebox
from datetime import datetime
from .base_view import BaseView
from ..services.dict_service import DictService
from ..services.multi_dict_service import MultiDictService
from ..services.word_family_service import WordFamilyService

class AddView(BaseView):
    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Create context menu
        self.create_context_menu()

        # 搜索锁，防止重复搜索
        self._search_lock = threading.Lock()
        self._searching = False

        # 使用 grid 布局实现按比例扩展
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3)  # 释义区域权重3
        self.grid_rowconfigure(3, weight=1)  # 来源语境区域权重1

        # Row 0: 搜索栏
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(20, 10), padx=5)

        self.entry_word = ctk.CTkEntry(top_frame, placeholder_text="输入单词...", width=400, height=45, font=("Microsoft YaHei UI", 15))
        self.entry_word.pack(side="left", padx=(0, 15))
        self.entry_word.bind("<Return>", lambda event: self.start_search())

        self.btn_search = ctk.CTkButton(top_frame, text="🔍 查询", width=90, height=45, font=("Microsoft YaHei UI", 14, "bold"), command=self.start_search)
        self.btn_search.pack(side="left", padx=5)

        self.btn_play_result = ctk.CTkButton(top_frame, text="🔊", width=50, height=45, fg_color="green", font=("Microsoft YaHei UI", 16), state="disabled")
        self.btn_play_result.pack(side="left", padx=5)

        # Row 1: 状态标签 + 释义标题
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=1, column=0, sticky="ew", padx=5)
        
        self.status_label = ctk.CTkLabel(header_frame, text="", text_color="gray", font=("Microsoft YaHei UI", 13))
        self.status_label.pack(side="left", anchor="w")
        
        ctk.CTkLabel(header_frame, text="📖 释义", font=("Microsoft YaHei UI", 14, "bold"), text_color="gray50").pack(side="right", anchor="e")

        # Row 2: Content Area (Dashboard or Results)
        self.result_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.result_container.grid(row=2, column=0, sticky="nsew", pady=(5, 15), padx=5)
        
        # Row 3: 来源语境区域（权重1，扩展较少）
        ctx_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray20"), border_width=1, border_color=("gray85", "gray30"), corner_radius=10)
        ctx_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 20), padx=5)

        head_frame = ctk.CTkFrame(ctx_frame, fg_color="transparent")
        head_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(head_frame, text="✍️ 来源语境 (粘贴原句)", font=("Microsoft YaHei UI", 14, "bold"), text_color="#3B8ED0").pack(side="left")

        self.btn_context_save = ctk.CTkButton(head_frame, text="💾 保存语境", width=100, height=30,
                                            fg_color="#3B8ED0", font=("Microsoft YaHei UI", 13, "bold"),
                                            command=self.save_context)
        self.btn_context_save.pack(side="right")

        self.txt_context_en = ctk.CTkTextbox(ctx_frame, height=80, font=("Microsoft YaHei UI", 15), fg_color="transparent", border_width=0)
        self.txt_context_en.pack(fill="x", padx=15, pady=(0, 5))

        line = ctk.CTkFrame(ctx_frame, height=1, fg_color="gray85")
        line.pack(fill="x", padx=15, pady=5)

        self.txt_context_cn = ctk.CTkTextbox(ctx_frame, height=60, font=("Microsoft YaHei UI", 14), text_color=("gray30", "gray70"), fg_color="transparent", border_width=0)
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
        trans = DictService.translate_text(text) or "翻译获取失败"
        self.after(0, lambda: self.update_trans_box(trans))

    def update_trans_box(self, text):
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        self.txt_context_cn.insert("0.0", text)

    def save_context(self):
        word = self.entry_word.get().strip()
        # Fallback to first word if empty? Maybe not in this decoupled view.
        # Original: or (self.vocab_list[0]['word'] if self.vocab_list else "")
        # We'll skip that fallback for safety.
        if not word:
            return

        ctx_en = self.txt_context_en.get("0.0", "end").strip()
        ctx_cn = self.txt_context_cn.get("0.0", "end").strip()

        if not ctx_cn or "⏳" in ctx_cn or "待粘贴" in ctx_cn:
            ctx_cn = DictService.translate_text(ctx_en) or ""
            self.update_trans_box(ctx_cn)

        self.controller.db.update_context(word, ctx_en, ctx_cn)
        self.controller.reload_vocab_list()

        messagebox.showinfo("成功", "例句已更新！")
        self.txt_context_en.delete("0.0", "end")
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        self.last_translated_text = ""

    def start_search(self):
        word = self.entry_word.get().strip()
        if not word:
            return

        # 使用锁防止重复搜索
        if not self._search_lock.acquire(blocking=False):
            return  # 如果锁已被占用，说明有搜索正在进行

        self.status_label.configure(text="查询中...", text_color="gray")
        self.btn_search.configure(state="disabled")
        self.btn_play_result.configure(state="disabled", fg_color="gray")
        self.txt_context_en.delete("0.0", "end")
        self.txt_context_cn.configure(state="normal")
        self.txt_context_cn.delete("0.0", "end")
        threading.Thread(target=self._search_thread_wrapper, args=(word,), daemon=True).start()

    def _search_thread_wrapper(self, word):
        try:
            self.search_word_thread(word)
        finally:
            self._search_lock.release()

    def search_word_thread(self, word):
        existing = self.controller.db.get_word(word)
        if existing:
            tags_str = f" [{existing['tags']}]" if existing.get('tags') else ""
            display = f"{existing['word']}  {existing.get('phonetic','')}{tags_str}\n\n[释义]\n{existing['meaning']}\n\n[例句]\n{existing['example']}"
            self.after(0, lambda: self.display_existing_word(existing, display))
            return

        # 1. 先获取有道结果 (保留原有的丰富数据: tags, roots, families)
        youdao_result = DictService.search_word(word)

        # 2. 并发查询其他词典
        agg_results = MultiDictService.aggregate_search(word, youdao_result=youdao_result)
        
        # 3. 确定主要结果 (优先使用有道，如果没有则取其他有的)
        primary_result = agg_results.get("primary")
        
        if primary_result:
            # === 构建聚合后的显示内容 ===
            sources_data = agg_results.get('sources', {})
            
            # A. 音标 (使用最佳音标)
            phonetic = MultiDictService.get_best_phonetic(sources_data)
            
            # B. 聚合释义
            display_parts = []
            display_parts.append(f"{word}  {phonetic}")
            
            # Tags (用户反馈太乱，不再显示)
            # tags = primary_result.get('tags', '')
            # if tags:
            #     display_parts[-1] += f" [{tags}]"

            # 分割线
            display_parts.append("-" * 30)

            # 各源释义
            combined_meanings = []
            # 优先级顺序
            source_order = [
                MultiDictService.DICT_YOUDAO, 
                MultiDictService.DICT_CAMBRIDGE, 
                MultiDictService.DICT_BING,
                MultiDictService.DICT_FREE
            ]
            
            for source_key in source_order:
                if source_key in sources_data:
                    data = sources_data[source_key]
                    source_name = MultiDictService.DICT_NAMES.get(source_key, source_key)
                    meaning = data.get('meaning', '').strip()
                    if meaning:
                        # 优化显示格式
                        combined_meanings.append(f"【{source_name}】\n{meaning}")
            
            full_meaning_str = "\n\n".join(combined_meanings)
            if full_meaning_str:
                display_parts.append(f"[释义]\n{full_meaning_str}")

            # C. 聚合例句
            all_examples = MultiDictService.get_all_examples(sources_data)
            if all_examples:
                display_parts.append("-" * 30)
                display_parts.append(f"[例句]\n{all_examples}")

            display = "\n".join(display_parts)

            # === 准备保存到数据库的数据 ===
            # 我们将聚合后的释义和例句保存，这样以后查看时也是多源的
            save_data = primary_result.copy()
            save_data['phonetic'] = phonetic
            save_data['meaning'] = full_meaning_str
            save_data['example'] = all_examples

            # Ensure date is present (fallback for non-Youdao sources)
            if 'date' not in save_data:
                save_data['date'] = datetime.now().strftime('%Y-%m-%d')

            # Add to DB
            self.controller.db.add_word(save_data)
            self.controller.reload_vocab_list()

            # Save word family associations (派生词关联) - 仅 Youdao 有
            word_families = save_data.get('word_families', [])
            for family in word_families:
                root = family.get('root', '')
                meaning = family.get('meaning', '')
                derivatives = family.get('derivatives', [])
                if root and derivatives:
                    all_words = [word] + derivatives
                    self.controller.db.add_word_families_batch(root, meaning, all_words)

            self.after(0, lambda: self.search_complete(display, "✅ 已保存", word, agg_results=agg_results))
        else:
            self.after(0, lambda: self.search_complete(None, "未找到该单词", None))

    def display_existing_word(self, item, text=None):
        self.btn_search.configure(state="normal")
        rc = item.get('review_count', 0)
        self.status_label.configure(text=f"✅ 已存在 (复习: {rc}次)", text_color="green")

        # 清空现有卡片
        for widget in self.result_container.winfo_children():
            widget.destroy()

        # 如果是从数据库读出的完整内容 (可能包含聚合信息)
        meaning = item.get('meaning', '').strip()
        example = item.get('example', '').strip()
        phonetic = item.get('phonetic', '')

        # 头部卡片 (单词 + 音标)
        self._create_header_card(item['word'], phonetic)

        # 尝试拆分已保存的聚合内容 (如果包含【...】标记)
        if "【" in meaning:
            import re
            parts = re.split(r'【(.*?)】', meaning)
            # parts[0] 是第一个【 之前的空字符串或内容
            for i in range(1, len(parts), 2):
                s_name = parts[i]
                s_content = parts[i+1].strip() if i+1 < len(parts) else ""
                self._create_source_card(s_name, s_content)
        else:
            # 兼容旧版本数据或单一源
            self._create_source_card("我的释义", meaning, example)

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
        self.entry_word.insert(0, item['word']) # Keep word in entry so context save works

        self.btn_play_result.configure(state="normal", fg_color="green", command=lambda: self.play_audio(item['word'], self.btn_play_result))
        self.after(500, lambda: self.play_audio(item['word'], self.btn_play_result))

    def search_complete(self, display_text, status, word, agg_results=None):
        self.btn_search.configure(state="normal")
        self.status_label.configure(text=status, text_color="green" if "✅" in status else "red")

        # 清空现有卡片
        for widget in self.result_container.winfo_children():
            widget.destroy()

        if agg_results:
            sources_data = agg_results.get('sources', {})
            phonetic = MultiDictService.get_best_phonetic(sources_data)
            
            # 1. 头部卡片
            self._create_header_card(word, phonetic)
            
            # 2. 词典源卡片
            source_order = [
                MultiDictService.DICT_YOUDAO, 
                MultiDictService.DICT_CAMBRIDGE, 
                MultiDictService.DICT_BING,
                MultiDictService.DICT_FREE
            ]
            
            for source_key in source_order:
                if source_key in sources_data:
                    data = sources_data[source_key]
                    s_name = MultiDictService.DICT_NAMES.get(source_key, source_key)
                    s_meaning = data.get('meaning', '').strip()
                    s_example = data.get('example', '').strip() if source_key == MultiDictService.DICT_YOUDAO else ""
                    if s_meaning:
                        self._create_source_card(s_name, s_meaning, s_example)
            
            # 3. 汇总例句卡片 (如果其他词典有例句)
            all_examples = MultiDictService.get_all_examples(sources_data)
            if all_examples:
                self._create_source_card("精选例句", "", all_examples, icon="📝")

        elif status != "✅ 已保存": # 出错提示
             self._show_info_card("提示", status, icon="ℹ️")

        if word:
            self.entry_word.delete(0, "end")
            self.btn_play_result.configure(state="normal", fg_color="green", command=lambda: self.play_audio(word, self.btn_play_result))
            self.after(500, lambda: self.play_audio(word, self.btn_play_result))

    # --- 新增内部布局方法 ---

    def _show_info_card(self, title, message, icon="💡"):
        card = ctk.CTkFrame(self.result_container, fg_color=("gray95", "#2b2b2b"), corner_radius=12)
        card.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(card, text=f"{icon} {title}", font=("Microsoft YaHei UI", 16, "bold"), text_color="#3B8ED0").pack(pady=(15, 5), padx=20, anchor="w")
        ctk.CTkLabel(card, text=message, font=("Microsoft YaHei UI", 13), text_color=("gray40", "gray70"), wraplength=700, justify="left").pack(pady=(0, 15), padx=20, anchor="w")

    def _create_header_card(self, word, phonetic):
        card = ctk.CTkFrame(self.result_container, fg_color=("white", "#1e1e1e"), corner_radius=15, border_width=1, border_color=("gray90", "gray30"))
        card.pack(fill="x", pady=(0, 10), padx=5)
        
        # 单词大字号
        word_label = ctk.CTkLabel(card, text=word, font=("Microsoft YaHei UI", 32, "bold"), text_color=("#1a1a1a", "#ffffff"))
        word_label.pack(side="left", padx=(25, 15), pady=25)
        
        # 音标
        if phonetic:
            ctk.CTkLabel(card, text=phonetic, font=("Microsoft YaHei UI", 16), text_color="#3B8ED0").pack(side="left", pady=30)
            
        # 播放按钮 (快捷)
        btn_p = ctk.CTkButton(card, text="🔊", width=45, height=45, corner_radius=22, fg_color="#4CAF50", hover_color="#45a049",
                            command=lambda: self.play_audio(word, btn_p))
        btn_p.pack(side="right", padx=25)

    def _create_source_card(self, source_name, meaning, example="", icon="📚"):
        card = ctk.CTkFrame(self.result_container, fg_color=("white", "gray25"), corner_radius=12, border_width=1, border_color=("gray90", "gray30"))
        card.pack(fill="x", pady=8, padx=5)
        
        # 头部：词典源名称
        header = ctk.CTkFrame(card, fg_color=("gray95", "#333333"), height=35, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"{icon} {source_name}", font=("Microsoft YaHei UI", 13, "bold"), text_color=("gray20", "gray80")).pack(side="left", padx=15)
        
        # 内容区域
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=15)
        
        if meaning:
            # 使用 Textbox 显示释义，以支持选择和复制
            m_box = ctk.CTkTextbox(body, height=100, font=("Microsoft YaHei UI", 14), fg_color="transparent", border_width=0, activate_scrollbars=False)
            m_box.pack(fill="x")
            m_box.insert("0.0", meaning)
            m_box.configure(state="disabled")
            self.bind_context_menu(m_box)
            
            # 自适应高度 (估算)
            lines = meaning.count('\n') + 1
            m_box.configure(height=min(300, max(40, lines * 25)))

        if example:
            if meaning:
                ctk.CTkFrame(body, height=1, fg_color=("gray90", "gray35")).pack(fill="x", pady=10)
            
            e_box = ctk.CTkTextbox(body, height=80, font=("Microsoft YaHei UI", 13, "italic"), text_color=("gray40", "gray60"), fg_color="transparent", border_width=0, activate_scrollbars=False)
            e_box.pack(fill="x")
            e_box.insert("0.0", example)
            e_box.configure(state="disabled")
            self.bind_context_menu(e_box)
            
            # 自适应高度
            e_lines = example.count('\n') + 1
            e_box.configure(height=min(200, max(40, e_lines * 22)))

    def on_show(self):
        """When showing, focus entry and show dashboard if empty"""
        self.entry_word.focus_set()
        if not self.entry_word.get().strip():
            self._show_dashboard()

    def _show_dashboard(self):
        """Show home statistics and motivation cards"""
        # Clear existing
        for widget in self.result_container.winfo_children():
            widget.destroy()

        stats = self.controller.db.get_statistics()
        
        # 1. Motivation Card
        m_card = ctk.CTkFrame(self.result_container, fg_color=("#E3F2FD", "#1A237E"), corner_radius=15)
        m_card.pack(fill="x", pady=(0, 15), padx=10)
        
        hour = datetime.now().hour
        greeting = "早上好" if 5 <= hour < 12 else "下午好" if 12 <= hour < 18 else "晚上好"
        
        ctk.CTkLabel(m_card, text=f"✨ {greeting}，今天也要加油哦！", font=("Microsoft YaHei UI", 20, "bold"), text_color=("#1976D2", "#BBDEFB")).pack(pady=(25, 5), padx=30, anchor="w")
        ctk.CTkLabel(m_card, text="不积跬步，无以至千里；不积小流，无以成江海。", font=("Microsoft YaHei UI", 13), text_color=("#1976D2", "#90CAF9")).pack(pady=(0, 25), padx=30, anchor="w")

        # 2. Stats Row
        stats_frame = ctk.CTkFrame(self.result_container, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        
        # Quick helper for stat boxes
        def create_stat_box(parent, title, value, color_theme):
            box = ctk.CTkFrame(parent, fg_color=color_theme[0], corner_radius=15, border_width=1, border_color=color_theme[1])
            box.pack(side="left", fill="both", expand=True, padx=10)
            ctk.CTkLabel(box, text=title, font=("Microsoft YaHei UI", 13, "bold"), text_color=color_theme[2]).pack(pady=(20, 5))
            ctk.CTkLabel(box, text=str(value), font=("Consolas", 32, "bold"), text_color=color_theme[2]).pack(pady=(0, 20))

        # Blue
        create_stat_box(stats_frame, "📚 总词库", stats['total'], (("white", "#2b2b2b"), ("gray90", "gray30"), ("#3B8ED0", "#3B8ED0")))
        # Orange
        create_stat_box(stats_frame, "⏰ 待复习", stats['due_today'], (("white", "#2b2b2b"), ("gray90", "gray30"), ("#FF9800", "#FF9800")))
        # Green
        create_stat_box(stats_frame, "🏆 已掌握", stats['mastered'], (("white", "#2b2b2b"), ("gray90", "gray30"), ("#4CAF50", "#4CAF50")))

        # 3. Quick Tips Card
        t_card = ctk.CTkFrame(self.result_container, fg_color=("gray95", "#2b2b2b"), corner_radius=12)
        t_card.pack(fill="x", pady=15, padx=10)
        ctk.CTkLabel(t_card, text="💡 学习小贴士", font=("Microsoft YaHei UI", 14, "bold"), text_color="gray").pack(pady=(12, 5), padx=20, anchor="w")
        tips = [
            "• 使用 Ctrl+N / L / R 快速在主页、列表和复习间切换",
            "• 在复习时，如果觉得太简单，可以直接标记为‘已掌握’",
            "• 您可以在设置中开启更多词典源，获得更丰富的释义"
        ]
        for tip in tips:
            ctk.CTkLabel(t_card, text=tip, font=("Microsoft YaHei UI", 12), text_color="gray", justify="left").pack(padx=20, anchor="w")
        ctk.CTkLabel(t_card, text="", height=5).pack() # Bottom padding

    def load_word(self, item):
        """Called by List View to show details"""
        tags_str = f" [{item['tags']}]" if item.get('tags') else ""
        display = f"{item['word']}  {item.get('phonetic','')}{tags_str}\n\n[释义]\n{item['meaning']}\n\n[例句]\n{item['example']}"
        self.display_existing_word(item, display)

    def create_context_menu(self):
        # Configure menu font
        menu_font = ("Microsoft YaHei UI", 12)

        self.context_menu = tk.Menu(self, tearoff=0, font=menu_font)
        self.context_menu.add_command(label="复制 (Copy)", command=self.on_copy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="查词 (Look up)", command=self.on_lookup_recursive)
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

    def on_lookup_recursive(self):
        text = self.get_selected_text()
        if text:
            word = text.strip()
            if not word: return

            # Populate entry and trigger search directly in current view
            self.entry_word.delete(0, "end")
            self.entry_word.insert(0, word)
            self.after(50, self.start_search)
