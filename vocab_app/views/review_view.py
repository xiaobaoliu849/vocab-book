import customtkinter as ctk
import tkinter as tk
import random
import threading
from datetime import datetime
from .base_view import BaseView
from ..services.review_service import ReviewService
from ..config import FONT_NORMAL, FONT_BOLD, FONT_LARGE

class ReviewView(BaseView):
    def setup_ui(self):
        self.configure(fg_color="transparent")
        self.create_context_menu()

        self.review_method = "flashcard" # "flashcard", "spelling", "sentence"
        self.is_cram_mode = False
        
        # UI State
        self.spelling_checked = False
        self.queue = []
        self.cur_word = None
        self.review_completed = 0
        self.review_total = 0
        self._queue_lock = threading.Lock()
        self._event_bound = False

        # --- Top Header: Mode Switcher ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", side="top", padx=60, pady=(20, 0))

        self.mode_frame = ctk.CTkFrame(self.header_frame, fg_color=("gray90", "#2b2b2b"), height=40, corner_radius=20)
        self.mode_frame.pack(side="left", pady=2)

        self.btn_method_flashcard = ctk.CTkButton(self.mode_frame, text="🎴 识记 (L1)", width=100, height=32, corner_radius=16, 
                                                fg_color="#3B8ED0", font=("Microsoft YaHei UI", 12, "bold"),
                                                command=lambda: self.set_review_method("flashcard"))
        self.btn_method_flashcard.pack(side="left", padx=2, pady=2)

        self.btn_method_spelling = ctk.CTkButton(self.mode_frame, text="⌨️ 拼写 (L2)", width=100, height=32, corner_radius=16, 
                                               fg_color=("gray90", "#2b2b2b"), text_color=("gray20", "gray80"), font=("Microsoft YaHei UI", 12),
                                               command=lambda: self.set_review_method("spelling"))
        self.btn_method_spelling.pack(side="left", padx=2, pady=2)

        self.btn_method_sentence = ctk.CTkButton(self.mode_frame, text="✍️ 语境 (L3)", width=100, height=32, corner_radius=16, 
                                               fg_color=("gray90", "#2b2b2b"), text_color=("gray20", "gray80"), font=("Microsoft YaHei UI", 12),
                                               command=lambda: self.set_review_method("sentence"))
        self.btn_method_sentence.pack(side="left", padx=2, pady=2)

        self.btn_toggle_cram = ctk.CTkButton(self.header_frame, text="🚀 突击模式: 关", width=140, height=36, corner_radius=18,
                                           fg_color="transparent", border_width=1, border_color="gray", 
                                           text_color=("gray20", "gray80"), font=("Microsoft YaHei UI", 12),
                                           command=self.toggle_cram_mode)
        self.btn_toggle_cram.pack(side="right")

        # Row 2: Progress (Moved inside card or kept top)
        self.progress_container = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_container.pack(fill="x", side="top", padx=80, pady=(10, 5)) 
        
        self.review_progress_bar = ctk.CTkProgressBar(self.progress_container, height=4, fg_color=("gray85", "gray30"), progress_color="#3B8ED0")
        self.review_progress_bar.pack(fill="x", side="top", pady=(0, 2))
        self.review_progress_bar.set(0)

        self.lbl_review_progress = ctk.CTkLabel(self.progress_container, text="待复习: 0 个", font=("Microsoft YaHei UI", 11), text_color="gray")
        self.lbl_review_progress.pack(side="right")

        # Row 3: Main Display Card (Responsive)
        self.card = ctk.CTkFrame(self, fg_color=("white", "#2b2b2b"), corner_radius=28, border_width=1, border_color=("gray90", "gray30"))
        self.card.pack(side="top", padx=60, pady=(10, 10), fill="both", expand=True) 
        # self.card.pack_propagate(False) # Removed to allow internal elements to push/pull

        self.lbl_rw = ctk.CTkTextbox(
            self.card, 
            height=80,
            font=("Microsoft YaHei UI", 36, "bold"),
            fg_color="transparent",
            text_color=("#1a1a1a", "#ffffff"),
            border_width=0,
            wrap="word",
            padx=10, 
            pady=0
        )
        # Hide scrollbar
        try:
            if hasattr(self.lbl_rw, "_v_scrollbar"):
                self.lbl_rw._v_scrollbar.grid_forget()
                self.lbl_rw._v_scrollbar.pack_forget()
        except AttributeError:
            pass
        
        self.lbl_rw.insert("0.0", "🎯 准备开始复习")
        self.lbl_rw.configure(state="disabled")
        self.lbl_rw.pack(pady=(60, 10), fill="x", padx=40)
        self.bind_context_menu(self.lbl_rw)

        self.btn_rp = ctk.CTkButton(self.card, text="🔊", width=46, height=46, corner_radius=23, fg_color="#4CAF50", hover_color="#45a049", font=("Arial", 18), command=lambda: None)
        self.btn_rp.pack(pady=5)

        self.txt_rm = ctk.CTkTextbox(self.card, font=("Microsoft YaHei UI", 15), fg_color="transparent", border_width=0, activate_scrollbars=True)
        self.txt_rm.pack(pady=(5, 10), fill="both", expand=True, padx=40)
        self.bind_context_menu(self.txt_rm)

        # Row 4: Integrated Exercise Desk (Bottom Area)
        self.desk_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.desk_frame.pack(side="top", fill="x", padx=40, pady=(0, 5))

        # Sub-container: Reveal Button (Standard)
        self.reveal_overlay = ctk.CTkFrame(self.desk_frame, fg_color="transparent")
        self.btn_rev = ctk.CTkButton(self.reveal_overlay, text="🔍 显示释义 (Space)", font=("Microsoft YaHei UI", 16, "bold"), width=300, height=55, corner_radius=28, command=self.reveal_meaning)
        self.btn_rev.pack(expand=True)

        # Sub-container: Active Exercise (Spelling/Sentence)
        self.exercise_overlay = ctk.CTkFrame(self.desk_frame, fg_color=("gray95", "#1e1e1e"), corner_radius=15, border_width=1, border_color=("gray90", "gray30"))
        
        self.lbl_ex_hint = ctk.CTkLabel(self.exercise_overlay, text="请输入拼写...", font=("Microsoft YaHei UI", 13), text_color="gray")
        self.lbl_ex_hint.pack(pady=(15, 5))

        self.entry_ex = ctk.CTkEntry(self.exercise_overlay, placeholder_text="Type here...", width=400, height=50, font=("Consolas", 20), justify="center", border_width=2)
        self.entry_ex.pack(pady=(0, 15), padx=40)
        self.entry_ex.bind("<Return>", lambda e: self.check_exercise())

        self.lbl_ex_result = ctk.CTkLabel(self.exercise_overlay, text="", font=("Microsoft YaHei UI", 15, "bold"))
        self.lbl_ex_result.pack(pady=(0, 10))

        # Sub-container: Mastery Actions (Post-reveal)
        self.act_frame = ctk.CTkFrame(self.desk_frame, fg_color="transparent")
        ctk.CTkButton(self.act_frame, text="忘了 (1)", fg_color="#F44336", hover_color="#D32F2F", width=120, height=45, corner_radius=22, font=("Microsoft YaHei UI", 14, "bold"), command=lambda: self.process_review_sm2(1)).pack(side="left", padx=15)
        ctk.CTkButton(self.act_frame, text="模糊 (2)", fg_color="#FF9800", hover_color="#F57C00", width=120, height=45, corner_radius=22, font=("Microsoft YaHei UI", 14, "bold"), command=lambda: self.process_review_sm2(3)).pack(side="left", padx=15)
        ctk.CTkButton(self.act_frame, text="熟悉 (3)", fg_color="#4CAF50", hover_color="#388E3C", width=120, height=45, corner_radius=22, font=("Microsoft YaHei UI", 14, "bold"), command=lambda: self.process_review_sm2(5)).pack(side="left", padx=15)

    def set_review_method(self, method):
        if method == self.review_method: return
        self.review_method = method

        # Update Buttons
        for m, btn in [("flashcard", self.btn_method_flashcard), ("spelling", self.btn_method_spelling), ("sentence", self.btn_method_sentence)]:
            if m == method:
                btn.configure(fg_color="#3B8ED0", text_color="white")
            else:
                btn.configure(fg_color=("gray90", "#2b2b2b"), text_color=("gray20", "gray80"))

        self.start_review()

    def on_show(self):
        self.start_review()

    def start_review(self):
        self.controller.reload_vocab_list()
        vocab_list = self.controller.vocab_list
        now_ts = datetime.now().timestamp()

        self.queue = []
        for w in vocab_list:
            if w.get('mastered', False) and not self.is_cram_mode: continue
            next_time = w.get('next_review_time', 0)
            if self.is_cram_mode or next_time <= now_ts:
                self.queue.append(w)

        random.shuffle(self.queue)
        self.review_total = len(self.queue)
        self.review_completed = 0
        self.cur_word = None
        self.spelling_checked = False
        self._event_bound = False 
        
        # Unified entry point
        self.next_card()
        self.bind_keys()

    def on_lookup(self):
        """Override: switch to Add view and search selected word"""
        text = self.get_selected_text()
        if text:
            word = self.clean_word(text)  # Clean punctuation
            if not word:
                return
            self.controller.show_frame("add")
            if "add" in self.controller.frames:
                add_view = self.controller.frames["add"]
                add_view.entry_word.delete(0, "end")
                add_view.entry_word.insert(0, word)
                add_view.after(100, add_view.start_search)
        self.bind_keys()

    def bind_keys(self):
        self.controller.bind("<space>", lambda e: self.on_space_key())

        def handle_key(quality):
             # Enable hotkeys if mastery grading buttons are shown (any mode)
             if self.act_frame.winfo_manager(): # Check if packed
                 self.process_review_sm2(quality)

        self.controller.bind("1", lambda e: handle_key(1))
        self.controller.bind("2", lambda e: handle_key(3))
        self.controller.bind("3", lambda e: handle_key(5))
        self.controller.bind("<Left>", lambda e: handle_key(1))
        self.controller.bind("<Right>", lambda e: handle_key(5))


    def toggle_cram_mode(self):
        self.is_cram_mode = not self.is_cram_mode

        if self.is_cram_mode:
            self.btn_toggle_cram.configure(text="🚀 突击模式: 开", fg_color="#E91E63") # Pinkish for active
        else:
            self.btn_toggle_cram.configure(text="🚀 突击模式: 关", fg_color="gray")

        self.start_review()

    def next_card(self):
        self.txt_rm.configure(state="normal")
        self.txt_rm.delete("0.0", "end")
        self.txt_rm.configure(state="disabled")
        
        # Reset Desk State
        for child in [self.reveal_overlay, self.exercise_overlay, self.act_frame]:
            child.pack_forget()

        self.spelling_checked = False
        self.entry_ex.configure(state="normal", border_color="gray")
        self.entry_ex.delete(0, "end")
        self.lbl_ex_result.configure(text="")

        remaining = len(self.queue)
        if self.review_total > 0:
            progress = self.review_completed / self.review_total
            self.review_progress_bar.set(progress)
            self.lbl_review_progress.configure(text=f"进度: {self.review_completed}/{self.review_total}  剩余: {remaining} 个")
        else:
            self.review_progress_bar.set(1)
            self.lbl_review_progress.configure(text="无待复习单词")


        if not self.queue:
            self.show_finished_screen()
            return

        self.cur_word = self.queue[0]
        word = self.cur_word['word']
        example = self.cur_word.get('example', '')
        context = self.cur_word.get('context_en', '')

        # Dispatch to mode-specific handlers
        method_handlers = {
            "flashcard": self._setup_flashcard_mode,
            "spelling": self._setup_spelling_mode,
            "sentence": self._setup_sentence_mode,
        }

        handler = method_handlers.get(self.review_method)
        if handler:
            handler(word, example, context)

        # Audio Play (Auto) - 使用类方法而非内部函数
        self.btn_rp.configure(command=self._safe_play_audio)
        if self.review_method != "spelling": # Don't play in spelling mode until revealed/checked? Standard learning practice.
            self._safe_play_audio()

    def _safe_play_audio(self):
        """安全播放当前单词发音（类方法，避免在循环中重复定义）"""
        if self.cur_word:
            self.play_audio(self.cur_word['word'])

    def _setup_flashcard_mode(self, word, example, context):
        """Setup flashcard (recognition) mode"""
        sentence = (example.split('\n')[0] if example else context)
        display_text = word
        if sentence:
            masked = self.get_cloze_text(sentence, word)
            if "____" in masked:
                display_text = masked
        self.update_lbl_rw(display_text, FONT_NORMAL if len(display_text) > 25 else FONT_LARGE)
        self.reveal_overlay.pack(expand=True, pady=10)

    def _setup_spelling_mode(self, word, example, context):
        """Setup spelling mode"""
        self.update_lbl_rw("⌨️ 单词拼写", FONT_LARGE)
        self.lbl_ex_hint.configure(text="根据释义拼写单词 (Enter 检查)")

        # Use the scrollable textbox for the meaning in spelling mode!
        self.txt_rm.configure(state="normal")
        self.txt_rm.insert("0.0", self._clean_display_text(self.cur_word.get('meaning', '')))
        self.txt_rm.configure(state="disabled")
        self.txt_rm.see("0.0")

        self.exercise_overlay.pack(fill="x", padx=40, pady=(0, 10))
        self.entry_ex.focus_set()

    def _setup_sentence_mode(self, word, example, context):
        """Setup sentence dictation mode"""
        sentence = (example.split('\n')[0] if example else context)
        if not sentence:
            self.update_lbl_rw("⌨️ 拼写练习 (无语境)", FONT_NORMAL)
            self.lbl_ex_hint.configure(text="暂无语境，请根据释义拼写")
        else:
            self.update_lbl_rw(self.get_cloze_text(sentence, word), FONT_NORMAL)
            self.lbl_ex_hint.configure(text="填空练习 (补全单词并回车)")

        # Also show meaning in textbox as a hint
        self.txt_rm.configure(state="normal")
        self.txt_rm.insert("0.0", self._clean_display_text(self.cur_word.get('meaning', '')))
        self.txt_rm.configure(state="disabled")
        self.txt_rm.see("0.0")

        self.exercise_overlay.pack(fill="x", padx=40, pady=(0, 10))
        self.entry_ex.focus_set()

    def get_cloze_text(self, sentence, word):
        """Replace the word (and its common variations) with blanks."""
        import re
        clean_word = word.strip().lower()
        # Pattern to match the word at word boundaries, case-insensitive
        pattern = re.compile(rf'\b{re.escape(clean_word)}\w*\b', re.IGNORECASE)
        masked = pattern.sub(" ____ ", sentence)
        return self._clean_display_text(masked)

    def update_lbl_rw(self, text, font):
        """Helper to update the selectable 'label' with dynamic height."""
        self.lbl_rw.configure(state="normal")
        self.lbl_rw.delete("0.0", "end")
        self.lbl_rw.insert("0.0", text)
        
        # Calculate height
        import re
        lines = text.count('\n') + 1
        est_lines = max(lines, len(text) // 30 + 1)
        font_size = font[1] if isinstance(font, (tuple, list)) else 24
        calc_height = est_lines * (font_size + 12) + 10
        
        self.lbl_rw.configure(height=calc_height, font=font, state="disabled")

    def _clean_display_text(self, text):
        """Standardize punctuation spacing to prevent ugly wrapping."""
        if not text: return ""
        import re
        # Remove space before punctuation: "word ." -> "word."
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        # Ensure space after punctuation if followed by text
        text = re.sub(r'([.,!?;:])([a-zA-Z])', r'\1 \2', text)
        return text.strip()

    def reveal_meaning(self):
        if not self.cur_word: return
        self.update_lbl_rw(self.cur_word['word'], FONT_LARGE)

        txt = f"{self.cur_word.get('phonetic','')}\n\n[释义]\n{self.cur_word.get('meaning', '')}"
        
        examples = self.cur_word.get('example', '')
        if examples:
             txt += f"\n\n[精选例句]\n{self._clean_display_text(examples)}"
             
        context = self.cur_word.get('context_en', '')
        if context:
            context_cn = self.cur_word.get('context_cn', '')
            txt += f"\n\n[✍️ 来源语境]\n{self._clean_display_text(context)}"
            if context_cn:
                txt += f"\n{context_cn}"

        self.txt_rm.configure(state="normal")
        self.txt_rm.insert("0.0", txt)
        self.txt_rm.configure(state="disabled")
        self.txt_rm.see("0.0")

        # Switch to action desk
        for child in [self.reveal_overlay, self.exercise_overlay]: child.pack_forget()
        self.act_frame.pack(side="top", pady=20)
        self.play_audio(self.cur_word['word'])

    def check_exercise(self):
        if not self.cur_word or self.spelling_checked: return

        user_input = self.entry_ex.get().strip().lower()
        correct = self.cur_word['word'].strip().lower()

        self.spelling_checked = True
        self.entry_ex.configure(state="disabled")
        self._pending_reveal_id = None  # 用于存储延迟调用的 ID

        if user_input == correct:
            self.lbl_ex_result.configure(text="✅ 拼写正确！点击任意处继续", text_color="#4CAF50")
            self.entry_ex.configure(border_color="#4CAF50")
            self.update_idletasks()
            self._pending_reveal_id = self.after(800, self._do_reveal_meaning)
        else:
            self.lbl_ex_result.configure(text=f"❌ 拼写有误 (正确: {correct}) 点击任意处继续", text_color="#F44336")
            self.entry_ex.configure(border_color="#F44336")
            self.update_idletasks()
            self._pending_reveal_id = self.after(2000, self._do_reveal_meaning)

        # 绑定点击事件，允许用户跳过等待
        self.exercise_overlay.bind("<Button-1>", self._skip_delay_and_reveal)
        self.lbl_ex_result.bind("<Button-1>", self._skip_delay_and_reveal)

    def _skip_delay_and_reveal(self, event=None):
        """允许用户点击跳过延迟，立即显示释义"""
        if self._pending_reveal_id:
            self.after_cancel(self._pending_reveal_id)
            self._pending_reveal_id = None
        # 解除绑定
        try:
            self.exercise_overlay.unbind("<Button-1>")
            self.lbl_ex_result.unbind("<Button-1>")
        except Exception:
            pass
        self._do_reveal_meaning()

    def _do_reveal_meaning(self):
        """实际执行显示释义的逻辑"""
        self._pending_reveal_id = None
        # 解除绑定（如果还没解除）
        try:
            self.exercise_overlay.unbind("<Button-1>")
            self.lbl_ex_result.unbind("<Button-1>")
        except Exception:
            pass
        self.reveal_meaning()

    def process_review_sm2(self, quality):
        if not self.cur_word: return
        word = self.cur_word['word']

        easiness, interval, repetitions = ReviewService.calculate_sm2(quality, self.cur_word)
        next_ts = ReviewService.calculate_next_review_time(interval)

        self.controller.db.update_sm2_status(word, easiness, interval, repetitions, next_ts, quality)
        self.controller.reload_vocab_list()

        with self._queue_lock:
            if not self.queue:
                self.next_card()
                return
            self.queue.pop(0)
            if quality >= 3:
                self.review_completed += 1
            else:
                # Re-insert for short term
                updated_word = self.controller.db.get_word(word)
                if updated_word:
                    insert_pos = random.randint(1, len(self.queue)) if len(self.queue) > 0 else 0
                    self.queue.insert(insert_pos, updated_word)

        self.next_card()

    def on_space_key(self):
        if self.review_method == "flashcard":
             if self.reveal_overlay.winfo_viewable():
                 self.reveal_meaning()
        else:
            if not self.spelling_checked:
                self.check_exercise()
            else:
                # If revealed, maybe Space doesn't do much or goes to next if 熟悉?
                # Usually Enter handles checking.
                pass

    def show_finished_screen(self):
        msg = "🎉 今日复习完毕！"
        self.update_lbl_rw(msg, ("Microsoft YaHei UI", 24, "bold"))
        self.txt_rm.configure(state="normal")
        self.txt_rm.delete("0.0", "end")
        self.txt_rm.insert("0.0", "\n\n        所有待复习单词已完成。您可以尝试‘突击模式’或切换复习模式。")
        self.txt_rm.configure(state="disabled")
        for child in [self.reveal_overlay, self.exercise_overlay, self.act_frame]: child.pack_forget()
        self.review_progress_bar.set(1)
        self.lbl_review_progress.configure(text=f"已完成 {self.review_completed} 个单词")
