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

        self.review_method = "flashcard" # "flashcard" or "spelling"
        self.is_cram_mode = False        # True or False

        self.queue = []
        self.cur_word = None
        self.review_completed = 0
        self.review_total = 0
        self._queue_lock = threading.Lock()  # 队列操作锁
        self._event_bound = False  # 事件绑定状态标志

        # Top Bar
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(10, 0))

        mode_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        mode_frame.pack(side="left")

        self.btn_method_flashcard = ctk.CTkButton(
            mode_frame, text="📖 闪卡模式", width=100, height=32,
            font=("Microsoft YaHei UI", 12, "bold"), fg_color="#3B8ED0",
            command=lambda: self.set_review_method("flashcard")
        )
        self.btn_method_flashcard.pack(side="left", padx=(0, 5))

        self.btn_method_spelling = ctk.CTkButton(
            mode_frame, text="✍️ 拼写模式", width=100, height=32,
            font=("Microsoft YaHei UI", 12, "bold"), fg_color="gray",
            command=lambda: self.set_review_method("spelling")
        )
        self.btn_method_spelling.pack(side="left")

        self.btn_toggle_cram = ctk.CTkButton(
            mode_frame, text="🚀 突击模式: 关", width=120, height=32,
            font=("Microsoft YaHei UI", 12, "bold"), fg_color="gray",
            command=self.toggle_cram_mode
        )
        self.btn_toggle_cram.pack(side="left", padx=(15, 0))

        progress_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        progress_frame.pack(side="right")

        self.lbl_review_progress = ctk.CTkLabel(
            progress_frame, text="待复习: 0 个", font=("Microsoft YaHei UI", 14), text_color="gray"
        )
        self.lbl_review_progress.pack(side="left", padx=(0, 10))

        self.review_progress_bar = ctk.CTkProgressBar(progress_frame, width=200, height=8)
        self.review_progress_bar.pack(side="left")
        self.review_progress_bar.set(0)

        # Flashcard UI
        self.card = ctk.CTkFrame(self, height=400, fg_color=("gray90", "gray20"))
        # Don't pack initially, handled by start_review or switch_mode
        self.card.pack_propagate(True)

        self.lbl_rw = ctk.CTkLabel(self.card, text="准备开始", font=FONT_LARGE)
        self.lbl_rw.pack(pady=(40, 10))

        self.btn_rp = ctk.CTkButton(self.card, text="🔊", width=40, fg_color="green", command=lambda: None)
        self.btn_rp.pack(pady=5)

        self.txt_rm = ctk.CTkTextbox(self.card, width=500, height=200, font=FONT_NORMAL, fg_color="transparent")
        self.txt_rm.pack(pady=10, fill="both", expand=True, padx=20)
        self.bind_context_menu(self.txt_rm)

        self.btn_rev = ctk.CTkButton(self, text="显示释义 (Space)", font=FONT_BOLD, width=200, height=45, command=self.reveal_meaning)

        self.act_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkButton(self.act_frame, text="忘记 (1)", fg_color="#F44336", width=100, height=40,
                     command=lambda: self.process_review_sm2(1)).pack(side="left", padx=10)
        ctk.CTkButton(self.act_frame, text="模糊 (2)", fg_color="#FF9800", width=100, height=40,
                     command=lambda: self.process_review_sm2(3)).pack(side="left", padx=10)
        ctk.CTkButton(self.act_frame, text="熟悉 (3)", fg_color="#4CAF50", width=100, height=40,
                     command=lambda: self.process_review_sm2(5)).pack(side="left", padx=10)

        # Spelling UI
        self.spelling_card = ctk.CTkFrame(self, height=550, fg_color=("gray90", "gray20"))
        self.spelling_card.pack_propagate(False)

        self.lbl_spelling_hint = ctk.CTkLabel(self.spelling_card, text="根据释义拼写单词", font=("Microsoft YaHei UI", 14), text_color="gray")
        self.lbl_spelling_hint.pack(pady=(20, 5))

        self.txt_spelling_meaning = ctk.CTkTextbox(self.spelling_card, width=600, height=260, font=("Microsoft YaHei UI", 15), fg_color="transparent")
        self.txt_spelling_meaning.pack(pady=10, padx=20)
        self.txt_spelling_meaning.configure(state="disabled")
        self.bind_context_menu(self.txt_spelling_meaning)

        self.btn_spelling_play = ctk.CTkButton(self.spelling_card, text="🔊 听发音", width=100, height=35, fg_color="green", font=("Microsoft YaHei UI", 13), command=lambda: None)
        self.btn_spelling_play.pack(pady=5)

        input_frame = ctk.CTkFrame(self.spelling_card, fg_color="transparent")
        input_frame.pack(pady=20, fill="x", padx=40)

        self.entry_spelling = ctk.CTkEntry(input_frame, placeholder_text="输入单词拼写...", width=350, height=50, font=("Microsoft YaHei UI", 18), justify="center")
        self.entry_spelling.pack(side="left", padx=(0, 10))
        self.entry_spelling.bind("<Return>", lambda e: self.check_spelling())

        self.btn_check_spelling = ctk.CTkButton(input_frame, text="✓ 检查", width=80, height=50, font=("Microsoft YaHei UI", 14, "bold"), fg_color="#4CAF50", hover_color="#45a049", command=self.check_spelling)
        self.btn_check_spelling.pack(side="left")

        self.spelling_result_frame = ctk.CTkFrame(self.spelling_card, fg_color="transparent")
        self.spelling_result_frame.pack(fill="x", padx=20, pady=10)

        self.lbl_spelling_result = ctk.CTkLabel(self.spelling_result_frame, text="", font=("Microsoft YaHei UI", 16, "bold"))
        self.lbl_spelling_result.pack()
        self.lbl_correct_answer = ctk.CTkLabel(self.spelling_result_frame, text="", font=("Microsoft YaHei UI", 14))
        self.lbl_correct_answer.pack()

        self.btn_spelling_next = ctk.CTkButton(self, text="下一个 (Enter)", width=150, height=45, font=("Microsoft YaHei UI", 14, "bold"), command=self.spelling_next)

    def on_show(self):
        self.start_review()
        self.bind_keys()

    def start_review(self):
        self.controller.reload_vocab_list()
        vocab_list = self.controller.vocab_list
        now_ts = datetime.now().timestamp()

        self.queue = []
        for w in vocab_list:
            # If NOT cram mode, skip mastered words
            if w.get('mastered', False) and not self.is_cram_mode: continue

            next_time = w.get('next_review_time', 0)
            if self.is_cram_mode:
                # In cram mode, include EVERYTHING regardless of time/mastery status
                self.queue.append(w)
            elif next_time <= now_ts:
                self.queue.append(w)

        random.shuffle(self.queue)
        self.review_total = len(self.queue)
        self.review_completed = 0
        self.cur_word = None
        self.spelling_checked = False
        self._event_bound = False  # 重置事件绑定状态

        if self.review_method == "flashcard":
            self.spelling_card.pack_forget()
            self.btn_spelling_next.pack_forget()
            self.next_card()
        else:
            self.card.pack_forget()
            self.btn_rev.pack_forget()
            self.act_frame.pack_forget()
            self.next_spelling_card()

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

            # Switch to Add view and search
            self.controller.show_frame("add")
            if "add" in self.controller.frames:
                add_view = self.controller.frames["add"]
                add_view.entry_word.delete(0, "end")
                add_view.entry_word.insert(0, word)
                # Use after to allow UI to switch before starting search
                add_view.after(100, add_view.start_search)

        self.bind_keys()

    def bind_keys(self):
        self.controller.bind("<space>", lambda e: self.on_space_key())

        def handle_key(quality):
             # Check if buttons are actually visible (user has revealed meaning)
             # And we must be in flashcard METHOD (regardless of cram scope)
             if self.review_method == "flashcard" and self.act_frame.winfo_viewable():
                 self.process_review_sm2(quality)

        self.controller.bind("1", lambda e: handle_key(1))
        self.controller.bind("2", lambda e: handle_key(3))
        self.controller.bind("3", lambda e: handle_key(5))
        self.controller.bind("<Left>", lambda e: handle_key(1))
        self.controller.bind("<Right>", lambda e: handle_key(5))

    def set_review_method(self, method):
        if method == self.review_method: return
        self.review_method = method

        if method == "flashcard":
            self.btn_method_flashcard.configure(fg_color="#3B8ED0")
            self.btn_method_spelling.configure(fg_color="gray")
        else:
            self.btn_method_flashcard.configure(fg_color="gray")
            self.btn_method_spelling.configure(fg_color="#3B8ED0")

        self.start_review()

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
        # Ensure textbox is initially cleared and reset
        self.txt_rm.configure(state="disabled")

        self.btn_rev.pack(pady=20)
        self.act_frame.pack_forget()

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

        self.card.pack(fill="both", expand=True, pady=20, padx=20)
        self.cur_word = self.queue[0]

        # Cloze Deletion Logic
        word = self.cur_word['word']
        example = self.cur_word.get('example', '')
        context = self.cur_word.get('context_en', '')

        display_text = word
        hint_text = ""

        # Try to find a sentence to mask
        sentence = ""
        if example:
            sentence = example.split('\n')[0] # Use first line of example
        elif context:
            sentence = context

        if sentence:
            masked_sentence = self.get_cloze_text(sentence, word)
            if "____" in masked_sentence:
                display_text = masked_sentence
                hint_text = "(根据语境回想单词)"

        self.lbl_rw.configure(text=display_text, font=FONT_NORMAL if len(display_text) > 20 else FONT_LARGE)

        # Show a small hint if it's a cloze test
        if hint_text:
            self.txt_rm.configure(state="normal")
            self.txt_rm.insert("0.0", f"\n\n\n\n          {hint_text}")
            self.txt_rm.configure(state="disabled")

        # Use a safe play wrapper
        def safe_play():
            if self.cur_word:
                self.play_audio(self.cur_word['word'])

        self.btn_rp.configure(command=safe_play)
        safe_play()

    def get_cloze_text(self, sentence, word):
        """Replace the word (and its common variations) with blanks."""
        import re
        # Basic variations: word, words, worded, wording, word's
        # This is a simple regex-based approach
        pattern = re.compile(rf'\b{re.escape(word)}\w*\b', re.IGNORECASE)
        return pattern.sub(" ____ ", sentence)

    def show_finished_screen(self):
        vocab_list = self.controller.vocab_list
        future_count = sum(1 for w in vocab_list if not w.get('mastered', False) and w.get('next_review_time', 0) > datetime.now().timestamp())
        msg = "🎉 今日复习完成！"
        if future_count > 0:
            msg += f"\n还有 {future_count} 个单词未到复习时间"

        if not self.is_cram_mode:
            msg += "\n\n(可开启 '🚀 突击模式' 继续复习所有单词)"

        if self.review_method == "flashcard":
            self.lbl_rw.configure(text=msg)
            self.btn_rev.pack_forget()
        else:
            self.spelling_card.pack_forget()
            self.card.pack(fill="x", pady=20, padx=20)
            self.lbl_rw.configure(text=msg)
            self.btn_rev.pack_forget()
            self.txt_rm.pack_forget() # Hide text box on finish in spelling mode if needed, or clear it

        self.review_progress_bar.set(1)
        self.lbl_review_progress.configure(text=f"已完成 {self.review_completed} 个单词")

    def reveal_meaning(self):
        if not self.cur_word: return
        # Restore the word in the label if it was masked
        self.lbl_rw.configure(text=self.cur_word['word'], font=FONT_LARGE)

        txt = f"{self.cur_word.get('phonetic','')}\n\n[释义]\n{self.cur_word.get('meaning', '')}\n\n[字典例句]\n{self.cur_word.get('example', '')}"
        if self.cur_word.get('context_en'):
            txt += f"\n\n[✍️ 来源语境]\n{self.cur_word['context_en']}\n{self.cur_word.get('context_cn','')}"

        self.txt_rm.configure(state="normal")
        self.txt_rm.insert("0.0", txt)
        self.txt_rm.configure(state="disabled")
        self.btn_rev.pack_forget()
        self.act_frame.pack(pady=20)

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
            self.reveal_meaning()
        else:
            if self.spelling_checked:
                self.spelling_next()
            else:
                self.check_spelling()

    # Spelling mode methods
    def next_spelling_card(self):
        self.spelling_checked = False
        self.entry_spelling.configure(border_color="gray", state="normal")
        self.entry_spelling.delete(0, "end")
        self.lbl_spelling_result.configure(text="")
        self.lbl_correct_answer.configure(text="")
        self.btn_check_spelling.configure(state="normal", text="✓ 检查")
        self.btn_spelling_next.pack_forget()

        remaining = len(self.queue)
        if self.review_total > 0:
            progress = self.review_completed / self.review_total
            self.review_progress_bar.set(progress)
            self.lbl_review_progress.configure(text=f"进度: {self.review_completed}/{self.review_total}  剩余: {remaining} 个")

        if not self.queue:
            self.show_finished_screen()
            return

        self.spelling_card.pack(fill="x", pady=20, padx=20)
        self.cur_word = self.queue[0]

        meaning_text = f"{self.cur_word.get('phonetic', '')}\n\n{self.cur_word['meaning']}"

        # Cloze Deletion for Spelling Mode
        word = self.cur_word['word']
        example = self.cur_word.get('example', '')
        context = self.cur_word.get('context_en', '')
        sentence = (example.split('\n')[0] if example else context)

        if sentence:
            masked = self.get_cloze_text(sentence, word)
            if "____" in masked:
                meaning_text += f"\n\n[语境填空]\n{masked}"
        elif example:
             meaning_text += f"\n\n[例句] {example}"

        self.txt_spelling_meaning.configure(state="normal")
        self.txt_spelling_meaning.delete("0.0", "end")
        self.txt_spelling_meaning.insert("0.0", meaning_text)
        self.txt_spelling_meaning.configure(state="disabled")

        def safe_play_spelling():
            if self.cur_word:
                self.play_audio(self.cur_word['word'])

        self.btn_spelling_play.configure(command=safe_play_spelling)
        safe_play_spelling()
        self.entry_spelling.focus_set()

        # 避免重复绑定事件处理器
        if not self._event_bound:
            self.controller.unbind("<Return>")
            self.controller.bind("<Return>", lambda e: self.check_spelling())
            self._event_bound = True

    def check_spelling(self):
        if not self.cur_word or self.spelling_checked: return
        user_input_raw = self.entry_spelling.get().strip()
        user_input_clean = user_input_raw.lower().strip(".,;?!")
        correct_word_raw = self.cur_word['word'].strip()
        correct_word_clean = correct_word_raw.lower().strip(".,;?!")

        self.spelling_checked = True
        self.entry_spelling.configure(state="disabled")
        self.btn_check_spelling.configure(state="disabled")

        if user_input_clean == correct_word_clean:
            self.lbl_spelling_result.configure(text="✅ 正确！", text_color="green")
            self.lbl_correct_answer.configure(text=f"单词: {correct_word_raw}", text_color="green")
            self.entry_spelling.configure(border_color="green")
            self.spelling_correct = True
        else:
            self.lbl_spelling_result.configure(text="❌ 错误", text_color="red")
            self.lbl_correct_answer.configure(text=f"正确答案: {correct_word_raw}\n你的输入: {user_input_raw or '(空)'}", text_color="red")
            self.entry_spelling.configure(border_color="red")
            self.spelling_correct = False

        self.btn_spelling_next.pack(pady=20)
        self.btn_spelling_next.focus_set()
        self.controller.unbind("<Return>")
        self.controller.bind("<Return>", lambda e: self.spelling_next())
        self._event_bound = False  # 重置事件绑定状态

    def spelling_next(self):
        if not self.cur_word: return
        word = self.cur_word['word']
        ok = getattr(self, 'spelling_correct', False)

        stage = self.cur_word.get('stage', 0)
        new_stage, next_ts, mastered = ReviewService.calculate_simple_stage(ok, stage)

        self.controller.db.update_review_status(word, new_stage, next_ts, mastered)
        self.controller.reload_vocab_list()

        with self._queue_lock:
            if not self.queue:
                self.next_spelling_card()
                return
            self.queue.pop(0)

            if ok:
                self.review_completed += 1
            else:
                updated_word = self.controller.db.get_word(word)
                if updated_word:
                    insert_pos = random.randint(1, len(self.queue)) if len(self.queue) > 0 else 0
                    self.queue.insert(insert_pos, updated_word)

        self.next_spelling_card()
