import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from .base_view import BaseView

class ListView(BaseView):
    def setup_ui(self):
        self.configure(fg_color="transparent")

        # State
        self.page_size = 20
        self.current_page = 1
        self.total_pages = 1
        self.filtered_vocab_list = []
        self.search_query = ""
        self.status_filter = "全部"
        self.list_search_timer = None
        self.selected_words = set() # Store selected words (by word string)

        # Toolbar
        toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=5, pady=(0, 10))

        # Search
        self.list_search_entry = ctk.CTkEntry(
            toolbar_frame, placeholder_text="🔍 搜索单词...", width=200, height=38, font=("Microsoft YaHei UI", 14)
        )
        self.list_search_entry.pack(side="left", padx=(0, 8))
        self.list_search_entry.bind("<KeyRelease>", self.on_list_search_input)
        self.list_search_entry.bind("<Return>", lambda e: self.execute_list_search())

        self.btn_clear_search = ctk.CTkButton(
            toolbar_frame, text="✕", width=38, height=38,
            fg_color="transparent", text_color="gray", hover_color=("gray90", "gray25"),
            command=self.clear_list_search
        )
        self.btn_clear_search.pack(side="left", padx=(0, 15))

        # Filter
        self.filter_options = ["全部", "待复习", "已掌握", "新单词", "学习中"]
        self.filter_dropdown = ctk.CTkOptionMenu(
            toolbar_frame, values=self.filter_options, width=110, height=38,
            font=("Microsoft YaHei UI", 13), command=self.on_filter_change
        )
        self.filter_dropdown.set("全部")
        self.filter_dropdown.pack(side="left", padx=(0, 15))

        # Batch Actions
        self.btn_batch_master = ctk.CTkButton(
            toolbar_frame, text="✅ 标为已掌握", width=110, height=38,
            fg_color="#4CAF50", hover_color="#388E3C",
            command=self.batch_mark_mastered
        )
        self.btn_batch_master.pack(side="left", padx=(0, 5))

        self.btn_batch_export = ctk.CTkButton(
            toolbar_frame, text="📤 导出选中", width=100, height=38,
            fg_color="#2196F3", hover_color="#1976D2",
            command=self.batch_export
        )
        self.btn_batch_export.pack(side="left", padx=(0, 5))

        self.btn_batch_del = ctk.CTkButton(
            toolbar_frame, text="🗑️ 批量删除", width=100, height=38,
            fg_color="#F44336", hover_color="#D32F2F",
            command=self.batch_delete
        )
        self.btn_batch_del.pack(side="left")

        self.lbl_results_count = ctk.CTkLabel(
            toolbar_frame, text="", font=("Microsoft YaHei UI", 12), text_color="gray"
        )
        self.lbl_results_count.pack(side="right", padx=10)

        # List Area
        self.list_scroll = ctk.CTkScrollableFrame(
            self, label_text="单词列表", label_font=("Microsoft YaHei UI", 14, "bold")
        )
        self.list_scroll.pack(fill="both", expand=True)

        # Widget Pool
        self.row_pool = []
        for i in range(self.page_size):
            row = self.create_row_widget()
            self.row_pool.append(row)

        # Pagination controls
        self.create_pagination_controls()

        # Create context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="查看详情", command=self.on_context_view)
        self.context_menu.add_command(label="播放发音", command=self.on_context_play)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制单词", command=self.on_context_copy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除单词", command=self.on_context_delete)

        self.current_context_item = None

    def create_row_widget(self):
        row_frame = ctk.CTkFrame(self.list_scroll, fg_color="transparent")

        # Checkbox
        checkbox = ctk.CTkCheckBox(row_frame, text="", width=24, height=24, command=None)
        checkbox.pack(side="left", padx=(5, 5))

        status_label = ctk.CTkLabel(row_frame, text="", width=70, font=("Arial", 12, "bold"))
        status_label.pack(side="left")

        # Word container (Frame with click events to simulate button)
        content_btn = ctk.CTkFrame(
            row_frame, fg_color="transparent", corner_radius=6, cursor="hand2", height=40
        )
        content_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Labels inside content frame
        row_content = ctk.CTkFrame(content_btn, fg_color="transparent")
        row_content.pack(fill="both", expand=True, padx=5)

        word_label = ctk.CTkLabel(row_content, text="", font=("Microsoft YaHei UI", 15, "bold"), anchor="w")
        word_label.pack(side="left")

        phonetic_label = ctk.CTkLabel(row_content, text="", font=("Arial", 12), text_color="gray", anchor="w")
        phonetic_label.pack(side="left", padx=10)

        meaning_label = ctk.CTkLabel(row_content, text="", font=("Microsoft YaHei UI", 13), text_color=("gray40", "gray60"), anchor="w")
        meaning_label.pack(side="left", padx=10, fill="x", expand=True)

        # Hover and Click effects
        def on_enter(e, f=content_btn):
            f.configure(fg_color=("gray90", "gray25"))
        def on_leave(e, f=content_btn):
            f.configure(fg_color="transparent")

        content_btn.bind("<Enter>", on_enter)
        content_btn.bind("<Leave>", on_leave)

        # Bind click for all children to main frame handler
        def bind_click_recursive(widget, handler):
            widget.bind("<Button-1>", handler)
            for child in widget.winfo_children():
                bind_click_recursive(child, handler)

        self._bind_click = bind_click_recursive

        play_btn = ctk.CTkButton(
            row_frame, text="🔊", width=35, height=30, fg_color="transparent", text_color="green",
            hover_color=("gray90", "gray25"), border_width=1, border_color="green"
        )
        play_btn.pack(side="left", padx=2)

        delete_btn = ctk.CTkButton(
            row_frame, text="🗑️", width=35, height=30, fg_color="transparent", text_color="red",
            hover_color=("gray90", "gray25"), border_width=1, border_color="red"
        )
        delete_btn.pack(side="left", padx=2)

        return {
            'frame': row_frame,
            'checkbox': checkbox,
            'status': status_label,
            'content_btn': content_btn,
            'word_lbl': word_label,
            'phonetic_lbl': phonetic_label,
            'meaning_lbl': meaning_label,
            'play_btn': play_btn,
            'delete_btn': delete_btn
        }

    def update_row_widget(self, row, item, now_ts):
        word = item['word']

        row['checkbox'].configure(command=lambda w=word: self.toggle_selection(w))
        if word in self.selected_words:
            row['checkbox'].select()
        else:
            row['checkbox'].deselect()

        stage = item.get('stage', 0)
        next_time = item.get('next_review_time', 0)

        # Determine status icon and color
        if item.get('mastered'):
            status_icon, color = "🏆", "green"
        elif next_time == 0:
            status_icon, color = "🆕", "gray"
        elif next_time <= now_ts:
            status_icon, color = "🔴", "red"
        else:
            status_icon, color = "🟢", "blue"

        row['status'].configure(text=f"{status_icon} Lv.{stage}", text_color=color)

        # Update labels instead of one big button text
        row['word_lbl'].configure(text=item['word'])

        phonetic = item.get('phonetic', '')
        tags = item.get('tags', '')
        # Truncate tags if too long
        if tags and len(tags) > 15:
            tags = tags[:12] + "..."

        phonetic_text = f"{phonetic} [{tags}]" if tags else phonetic
        row['phonetic_lbl'].configure(text=phonetic_text)

        # Meaning truncation
        meaning_lines = item.get('meaning', '').splitlines()
        first_meaning = meaning_lines[0] if meaning_lines else ""
        if len(first_meaning) > 25:
            first_meaning = first_meaning[:25] + "..."
        row['meaning_lbl'].configure(text=first_meaning)

        # Setup main button command
        def on_row_click(e, x=item):
            self.view_word_detail(x)

        # Apply recursive binding for clicks
        self._bind_click(row['content_btn'], on_row_click)

        # Bind right click
        for widget in [row['content_btn'], row['word_lbl'], row['phonetic_lbl'], row['meaning_lbl']]:
            widget.bind("<Button-3>", lambda e, x=item: self.show_context_menu(e, x))
            widget.bind("<Button-2>", lambda e, x=item: self.show_context_menu(e, x))

        play_btn = row['play_btn']
        row['play_btn'].configure(command=lambda w=item['word'], b=play_btn: self.play_audio(w, b))
        row['delete_btn'].configure(command=lambda w=item['word']: self.delete_word(w))

    def toggle_selection(self, word):
        if word in self.selected_words:
            self.selected_words.remove(word)
        else:
            self.selected_words.add(word)

    def batch_delete(self):
        if not self.selected_words:
            messagebox.showinfo("提示", "请先选择要删除的单词")
            return

        count = len(self.selected_words)
        if messagebox.askyesno("批量删除", f"确定要删除选中的 {count} 个单词吗？\n此操作不可撤销。"):
            for word in list(self.selected_words): # iterate copy
                self.controller.db.delete_word(word)

            self.selected_words.clear()
            self.refresh_list()
            messagebox.showinfo("完成", "删除成功")

    def batch_mark_mastered(self):
        if not self.selected_words:
            messagebox.showinfo("提示", "请先选择单词")
            return

        count = len(self.selected_words)
        if messagebox.askyesno("批量操作", f"确定将选中的 {count} 个单词标记为已掌握吗？"):
            # Update DB for each selected word
            # Using update_review_status or similar logic, but since we just want to set mastered=1,
            # we might need a dedicated method in DB or reuse existing one.
            # update_review_status requires stage/next_time/mastered.
            # Let's add a simple batch update method in controller or DB, or just loop here.
            # Looping is fine for now as user won't select thousands at once usually.

            # However, to be clean, let's just use a direct SQL update in loop via a new DB method or existing one.
            # Reusing update_review_status might reset review count or history if not careful.
            # Let's add a specialized method in DatabaseManager first?
            # Or just use raw SQL via a helper if available.
            # Looking at database.py, we don't have a simple "set_mastered" method.
            # Let's define one locally or call a new method on DB.
            # Since I can't edit DB file in this turn easily without switching context,
            # I will assume I can add it or just use what I have.
            # Wait, I CAN edit DB file. But for now let's implement the logic assuming I'll add the method.

            for word in list(self.selected_words):
                # We need to preserve other fields? No, just set mastered=1.
                # But update_review_status updates stage and next_review_time too.
                # Let's use a new method `mark_word_mastered(word)` in DB.
                self.controller.db.mark_word_mastered(word)

            self.selected_words.clear()
            self.refresh_list()
            messagebox.showinfo("完成", "已全部标记为已掌握")

    def batch_export(self):
        if not self.selected_words:
            messagebox.showinfo("提示", "请先选择单词")
            return

        from tkinter import filedialog
        import csv

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="导出选中单词"
        )
        if not filename:
            return

        try:
            # Gather data for selected words
            selected_items = [
                item for item in self.controller.vocab_list
                if item['word'] in self.selected_words
            ]

            # Define CSV headers
            headers = ['word', 'phonetic', 'meaning', 'example', 'tags', 'mastered', 'stage']

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for item in selected_items:
                    writer.writerow({
                        'word': item.get('word', ''),
                        'phonetic': item.get('phonetic', ''),
                        'meaning': item.get('meaning', ''),
                        'example': item.get('example', ''),
                        'tags': item.get('tags', ''),
                        'mastered': 'Yes' if item.get('mastered') else 'No',
                        'stage': item.get('stage', 0)
                    })

            messagebox.showinfo("完成", f"成功导出 {len(selected_items)} 个单词")
            # Optional: clear selection? No, user might want to keep selection.
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def create_pagination_controls(self):
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.pack(fill="x", pady=(10, 5))

        nav_frame = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        nav_frame.pack(side="left")

        self.btn_prev = ctk.CTkButton(
            nav_frame, text="◀ 上一页", width=90, height=32, font=("Microsoft YaHei UI", 12),
            command=self.go_prev_page
        )
        self.btn_prev.pack(side="left", padx=5)

        self.lbl_page_info = ctk.CTkLabel(
            nav_frame, text="第 1 / 1 页", font=("Microsoft YaHei UI", 13, "bold"), width=100
        )
        self.lbl_page_info.pack(side="left", padx=10)

        self.btn_next = ctk.CTkButton(
            nav_frame, text="下一页 ▶", width=90, height=32, font=("Microsoft YaHei UI", 12),
            command=self.go_next_page
        )
        self.btn_next.pack(side="left", padx=5)

        size_frame = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        size_frame.pack(side="right")

        ctk.CTkLabel(size_frame, text="每页:", font=("Microsoft YaHei UI", 12)).pack(side="left", padx=(0, 5))
        self.page_size_dropdown = ctk.CTkOptionMenu(
            size_frame, values=["15", "20", "30", "50"], width=70, height=32,
            font=("Microsoft YaHei UI", 12), command=self.on_page_size_change
        )
        self.page_size_dropdown.set(str(self.page_size))
        self.page_size_dropdown.pack(side="left")

    def on_show(self):
        self.refresh_list()

    def refresh_list(self):
        self.controller.reload_vocab_list()
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def view_word_detail(self, item):
        from .detail_window import DetailWindow
        DetailWindow(self.controller, item, self.controller)

    def delete_word(self, word):
        if messagebox.askyesno("删除确认", f"确定要删除单词 \"{word}\" 吗？\n\n此操作不可撤销。"):
            self.controller.db.delete_word(word)
            if word in self.selected_words:
                self.selected_words.remove(word)
            self.refresh_list()

    # --- Context Menu ---
    def show_context_menu(self, event, item):
        self.current_context_item = item
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def on_context_view(self):
        if self.current_context_item:
            self.view_word_detail(self.current_context_item)

    def on_context_play(self):
        if self.current_context_item:
            self.play_audio(self.current_context_item['word'])

    def on_context_copy(self):
        if self.current_context_item:
            self.clipboard_clear()
            self.clipboard_append(self.current_context_item['word'])
            self.update() # Required for clipboard to work

    def on_context_delete(self):
        if self.current_context_item:
            self.delete_word(self.current_context_item['word'])

    # --- Search & Filter ---
    def _reset_and_render(self):
        """Common helper to reset page, apply filters, and render."""
        self.current_page = 1
        self.apply_filters()
        self.render_current_page()
        self.update_pagination_controls()

    def on_list_search_input(self, event=None):
        if self.list_search_timer:
            self.after_cancel(self.list_search_timer)
        self.list_search_timer = self.after(300, self.execute_list_search)

    def execute_list_search(self):
        self.search_query = self.list_search_entry.get().strip()
        self._reset_and_render()

    def clear_list_search(self):
        self.list_search_entry.delete(0, "end")
        self.search_query = ""
        self._reset_and_render()

    def on_filter_change(self, value):
        self.status_filter = value
        self._reset_and_render()

    def match_status_filter(self, item, now_ts):
        status = self.status_filter
        next_review_time = item.get('next_review_time', 0)
        is_mastered = item.get('mastered', False)

        if status == "全部":
            return True
        if status == "待复习":
            return not is_mastered and next_review_time != 0 and next_review_time <= now_ts
        if status == "已掌握":
            return is_mastered
        if status == "新单词":
            return next_review_time == 0
        if status == "学习中":
            return not is_mastered and next_review_time > now_ts
        return True

    def sort_vocab_list(self, items, now_ts):
        def sort_key(item):
            if item.get('mastered'): return (3, 0)
            next_time = item.get('next_review_time', 0)
            if next_time == 0: return (1, 0)
            elif next_time <= now_ts: return (0, next_time)
            else: return (2, next_time)
        return sorted(items, key=sort_key)

    def apply_filters(self):
        query = self.search_query.lower().strip()
        now_ts = datetime.now().timestamp()

        # Access vocab_list from controller
        vocab_list = self.controller.vocab_list

        result = []
        for item in vocab_list:
            if not self.match_status_filter(item, now_ts): continue
            if query:
                word_match = query in item.get('word', '').lower()
                meaning_match = query in (item.get('meaning') or '').lower()
                if not (word_match or meaning_match): continue
            result.append(item)

        self.filtered_vocab_list = self.sort_vocab_list(result, now_ts)
        total_items = len(self.filtered_vocab_list)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        if self.current_page > self.total_pages: self.current_page = self.total_pages
        self.lbl_results_count.configure(text=f"找到 {total_items} 个单词")

    def render_current_page(self):
        for row in self.row_pool:
            row['frame'].pack_forget()

        if not self.filtered_vocab_list:
            if self.row_pool:
                self.row_pool[0]['checkbox'].pack_forget() # Hide checkbox for empty msg
                self.row_pool[0]['status'].configure(text="", text_color="gray")
                self.row_pool[0]['content_btn'].configure(fg_color=("gray90", "gray25"))
                self.row_pool[0]['word_lbl'].configure(text="空空如也，快去添加单词吧！")
                self.row_pool[0]['phonetic_lbl'].configure(text="")
                self.row_pool[0]['meaning_lbl'].configure(text="")
                self.row_pool[0]['play_btn'].pack_forget()
                self.row_pool[0]['delete_btn'].pack_forget()
                self.row_pool[0]['frame'].pack(fill="x", pady=20, padx=5)
            return

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        page_items = self.filtered_vocab_list[start_idx:end_idx]
        now_ts = datetime.now().timestamp()

        while len(self.row_pool) < len(page_items):
            row = self.create_row_widget()
            self.row_pool.append(row)

        for i, item in enumerate(page_items):
            row = self.row_pool[i]
            row['checkbox'].pack(side="left", padx=(5, 5)) # Show checkbox
            row['play_btn'].pack(side="left", padx=2)
            row['delete_btn'].pack(side="left", padx=2)
            self.update_row_widget(row, item, now_ts)
            row['frame'].pack(fill="x", pady=2, padx=5)

        try:
            self.list_scroll._parent_canvas.yview_moveto(0)
        except (AttributeError, Exception):
            pass

    def update_pagination_controls(self):
        self.lbl_page_info.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled",
                               fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"] if self.current_page > 1 else "gray")
        self.btn_next.configure(state="normal" if self.current_page < self.total_pages else "disabled",
                               fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"] if self.current_page < self.total_pages else "gray")

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_current_page()
            self.update_pagination_controls()

    def go_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.render_current_page()
            self.update_pagination_controls()

    def on_page_size_change(self, value):
        self.page_size = int(value)
        self.current_page = 1
        self.apply_filters()
        while len(self.row_pool) < self.page_size:
            row = self.create_row_widget()
            self.row_pool.append(row)
        self.render_current_page()
        self.update_pagination_controls()
