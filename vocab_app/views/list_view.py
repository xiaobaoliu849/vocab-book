import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import re
import time
from datetime import datetime
from .base_view import BaseView
from ..config import FONT_NORMAL, FONT_BOLD, FONT_LARGE

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
        self._last_detail_open_time = 0 # Debounce for DetailWindow
        self.focused_index = -1  # Currently focused row index (keyboard navigation)

        # Toolbar
        toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=5, pady=(0, 10))

        # --- Search Box ---
        search_frame = ctk.CTkFrame(toolbar_frame, fg_color=("gray95", "#242424"), corner_radius=20, height=40)
        search_frame.pack(side="left", padx=(0, 10))
        search_frame.pack_propagate(False)

        search_icon = ctk.CTkLabel(search_frame, text="🔍", font=("Arial", 14))
        search_icon.pack(side="left", padx=(12, 5))

        self.list_search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="搜索单词...", border_width=0, 
            fg_color="transparent", width=180, font=("Microsoft YaHei UI", 13)
        )
        self.list_search_entry.pack(side="left", fill="y")
        self.list_search_entry.bind("<KeyRelease>", self.on_list_search_input)
        self.list_search_entry.bind("<Return>", lambda e: self.execute_list_search())

        self.btn_clear_search = ctk.CTkButton(
            search_frame, text="✕", width=28, height=28, corner_radius=14,
            fg_color="transparent", text_color="gray", hover_color=("gray85", "gray30"),
            command=self.clear_list_search
        )
        self.btn_clear_search.pack(side="right", padx=5)

        # --- Filter Pill ---
        self.filter_options = ["全部", "待复习", "已掌握", "新单词", "学习中"]
        self.filter_dropdown = ctk.CTkOptionMenu(
            toolbar_frame, values=self.filter_options, width=100, height=36, corner_radius=18,
            font=("Microsoft YaHei UI", 12), command=self.on_filter_change,
            fg_color=("#3B8ED0", "#1f538d"), button_color=("#3B8ED0", "#1f538d"),
            button_hover_color=("#3677ad", "#1a4675")
        )
        self.filter_dropdown.set("全部")
        self.filter_dropdown.pack(side="left", padx=(0, 15))

        # --- Batch Actions ---
        batch_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        batch_frame.pack(side="left")

        self.btn_batch_master = ctk.CTkButton(
            batch_frame, text="✅ 掌握", width=80, height=36, corner_radius=18,
            fg_color="#4CAF50", hover_color="#388E3C", font=("Microsoft YaHei UI", 12, "bold"),
            command=self.batch_mark_mastered
        )
        self.btn_batch_master.pack(side="left", padx=(0, 5))

        self.btn_batch_export = ctk.CTkButton(
            batch_frame, text="📤 导出", width=80, height=36, corner_radius=18,
            fg_color="#2196F3", hover_color="#1976D2", font=("Microsoft YaHei UI", 12, "bold"),
            command=self.batch_export
        )
        self.btn_batch_export.pack(side="left", padx=(0, 5))

        self.btn_batch_del = ctk.CTkButton(
            batch_frame, text="🗑️ 删除", width=80, height=36, corner_radius=18,
            fg_color="#F44336", hover_color="#D32F2F", font=("Microsoft YaHei UI", 12, "bold"),
            command=self.batch_delete
        )
        self.btn_batch_del.pack(side="left")

        self.lbl_results_count = ctk.CTkLabel(
            toolbar_frame, text="", font=("Microsoft YaHei UI", 12), text_color="gray"
        )
        self.lbl_results_count.pack(side="right", padx=10)

        # --- List Area ---
        self.list_scroll = ctk.CTkScrollableFrame(
            self, label_text="单词列表", 
            label_font=("Microsoft YaHei UI", 14, "bold"),
            fg_color="transparent", label_fg_color="transparent"
        )
        self.list_scroll.pack(fill="both", expand=True, pady=(5, 0))

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
        # Bind menu close event to restore row style
        self.context_menu.bind("<Unmap>", self._on_context_menu_close)

        self.current_context_item = None
        self.current_context_row = None  # Track highlighted row for context menu

        # Keyboard navigation bindings
        self.bind_keyboard_events()

    def bind_keyboard_events(self):
        """Bind keyboard events for list navigation"""
        # Bind to the scrollable frame and main view
        # Bind to controller (main window) for reliable keyboard capture
        self.controller.bind("<Up>", self._handle_key_up)
        self.controller.bind("<Down>", self._handle_key_down)
        self.controller.bind("<Return>", self._handle_key_enter)
        self.controller.bind("<Delete>", self._handle_key_delete)
        self.controller.bind("<Control-a>", self._handle_key_select_all)
        self.controller.bind("<Control-A>", self._handle_key_select_all)
        
    def _is_list_view_active(self):
        """Check if list view is currently visible and should handle keys"""
        return self.winfo_ismapped() and self.focused_index >= 0
    
    def _handle_key_up(self, event=None):
        if self._is_list_view_active():
            return self.on_key_up(event)
            self.on_key_up(event)
    def _handle_key_down(self, event=None):
        # Also activate on first keypress if list is visible
        if self.winfo_ismapped():
            return self.on_key_down(event)
            self.on_key_down(event)
    def _handle_key_enter(self, event=None):
        if self._is_list_view_active():
            return self.on_key_enter(event)
            self.on_key_enter(event)
    def _handle_key_delete(self, event=None):
        if self._is_list_view_active():
            return self.on_key_delete(event)
            self.on_key_delete(event)
    def _handle_key_select_all(self, event=None):
        if self.winfo_ismapped():
            return self.on_key_select_all(event)
            self.on_key_select_all(event)
        """Move focus to previous row"""
        if not self.filtered_vocab_list:
            return "break"
        
        # Calculate visible range
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        page_count = end_idx - start_idx
        
        if self.focused_index <= 0:
            # At top of page, go to previous page if possible
            if self.current_page > 1:
                self.go_prev_page()
                self.focused_index = min(self.page_size - 1, len(self.filtered_vocab_list) - (self.current_page - 1) * self.page_size - 1)
                self._update_focus_highlight()
        else:
            self.focused_index -= 1
            self._update_focus_highlight()
        
        return "break"
    
    def on_key_down(self, event=None):
        """Move focus to next row"""
        if not self.filtered_vocab_list:
            return "break"
        
        # Calculate visible range
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        page_count = end_idx - start_idx
        
        if self.focused_index < 0:
            # No focus yet, focus first item
            self.focused_index = 0
        elif self.focused_index >= page_count - 1:
            # At bottom of page, go to next page if possible
            if self.current_page < self.total_pages:
                self.go_next_page()
                self.focused_index = 0
                self._update_focus_highlight()
        else:
            self.focused_index += 1
        
        self._update_focus_highlight()
        return "break"
    
    def on_key_enter(self, event=None):
        """Open detail window for focused item"""
        if self.focused_index < 0 or not self.filtered_vocab_list:
            return "break"
        
        start_idx = (self.current_page - 1) * self.page_size
        actual_idx = start_idx + self.focused_index
        
        if 0 <= actual_idx < len(self.filtered_vocab_list):
            item = self.filtered_vocab_list[actual_idx]
            self.view_word_detail(item)
        
        return "break"
    
    def on_key_delete(self, event=None):
        """Delete focused item"""
        if self.focused_index < 0 or not self.filtered_vocab_list:
            return "break"
        
        start_idx = (self.current_page - 1) * self.page_size
        actual_idx = start_idx + self.focused_index
        
        if 0 <= actual_idx < len(self.filtered_vocab_list):
            item = self.filtered_vocab_list[actual_idx]
            self.delete_word(item['word'])
        
        return "break"
    
    def on_key_select_all(self, event=None):
        """Select all words in the current filtered list"""
        if not self.filtered_vocab_list:
            return "break"
        
        # Toggle: if all are selected, deselect all; otherwise select all
        all_words = {item['word'] for item in self.filtered_vocab_list}
        if all_words.issubset(self.selected_words):
            # All selected, deselect all
            self.selected_words.clear()
        else:
            # Select all
            self.selected_words = all_words.copy()
        
        # Update checkboxes
        self._update_checkboxes()
        return "break"
    
    def _update_focus_highlight(self):
        """Update visual highlight for keyboard-focused row"""
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        page_count = end_idx - start_idx
        
        for i in range(len(self.row_pool)):
            if i >= page_count:
                break
            row = self.row_pool[i]
            if i == self.focused_index:
                # Highlight focused row
                row['frame'].configure(
                    border_color=("#1f538d", "#3B8ED0"),
                    border_width=2,
                    fg_color=("gray95", "#363636")
                )
            else:
                # Normal style
                row['frame'].configure(
                    border_color=("gray90", "gray30"),
                    border_width=1,
                    fg_color=("white", "#2b2b2b")
                )
    
    def _update_checkboxes(self):
        """Update all visible checkbox states based on selected_words"""
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_vocab_list))
        
        for i, item in enumerate(self.filtered_vocab_list[start_idx:end_idx]):
            if i < len(self.row_pool):
                if item['word'] in self.selected_words:
                    self.row_pool[i]['checkbox'].select()
                else:
                    self.row_pool[i]['checkbox'].deselect()

    def create_row_widget(self):
        # Card container
        card = ctk.CTkFrame(
            self.list_scroll, fg_color=("white", "#2b2b2b"), corner_radius=16, 
            border_width=1, border_color=("gray90", "gray30")
        )
        card.grid_columnconfigure(1, weight=1) # Main content expands

        # Checkbox (Strict position)
        checkbox = ctk.CTkCheckBox(card, text="", width=20, height=20, corner_radius=6)
        checkbox.grid(row=0, column=0, padx=(15, 10), sticky="w", pady=15)

        # Content area (Clickable)
        content_btn = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        content_btn.grid(row=0, column=1, sticky="nsew", pady=10)
        content_btn.grid_columnconfigure(0, weight=1)

        # Header: Word + Level Badge
        header_container = ctk.CTkFrame(content_btn, fg_color="transparent")
        header_container.grid(row=0, column=0, sticky="ew")

        word_label = ctk.CTkLabel(header_container, text="", font=("Microsoft YaHei UI", 16, "bold"), anchor="w")
        word_label.pack(side="left")

        status_label = ctk.CTkLabel(
            header_container, text="", font=("Microsoft YaHei UI", 10, "bold"), 
            height=20, corner_radius=10, width=60
        )
        status_label.pack(side="left", padx=10)

        phonetic_label = ctk.CTkLabel(header_container, text="", font=("Arial", 12), text_color="gray", anchor="w")
        phonetic_label.pack(side="left")

        # Multiline Meaning
        meaning_label = ctk.CTkLabel(
            content_btn, text="", font=("Microsoft YaHei UI", 12), 
            text_color=("gray30", "gray70"), anchor="w", justify="left",
            wraplength=600 # Wider wrap
        )
        meaning_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Actions frame (Sticky right)
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=(5, 15), sticky="e")

        # Subtle Style: Low contrast by default, bright on hover
        play_btn = ctk.CTkButton(
            actions_frame, text="▶", width=30, height=30, corner_radius=15, 
            fg_color=("gray92", "gray28"), text_color=("#4CAF50", "#A5D6A7"),
            hover_color=("#4CAF50", "#2E7D32"), border_width=0,
            font=("Arial", 12, "bold")
        )
        play_btn.pack(side="left", padx=3)

        delete_btn = ctk.CTkButton(
            actions_frame, text="×", width=30, height=30, corner_radius=15, 
            fg_color=("gray92", "gray28"), text_color=("#F44336", "#EF9A9A"),
            hover_color=("#F44336", "#C62828"), border_width=0,
            font=("Arial", 14, "bold")
        )
        delete_btn.pack(side="left", padx=3)

        def set_actions_visibility(active):
            if active:
                play_btn.configure(fg_color=("#4CAF50", "#2E7D32"), text_color="white")
                delete_btn.configure(fg_color=("#F44336", "#C62828"), text_color="white")
            else:
                play_btn.configure(fg_color=("gray92", "gray28"), text_color=("#4CAF50", "#A5D6A7"))
                delete_btn.configure(fg_color=("gray92", "gray28"), text_color=("#F44336", "#EF9A9A"))

        # Hover and Click effects
        def on_enter(e, c=card):
            c.configure(border_color=("#3B8ED0", "#1f538d"), fg_color=("gray98", "#323232"))
            set_actions_visibility(True)
        def on_leave(e, c=card):
            c.configure(border_color=("gray90", "gray30"), fg_color=("white", "#2b2b2b"))
            set_actions_visibility(False)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        def bind_click_recursive(widget, single_handler, double_handler):
            # Don't bind to buttons or checkbox
            if widget not in [play_btn, delete_btn, checkbox]:
                widget.bind("<Button-1>", single_handler)
                widget.bind("<Double-Button-1>", double_handler)
                for child in widget.winfo_children():
                    bind_click_recursive(child, single_handler, double_handler)

        self._bind_click = bind_click_recursive

        return {
            'frame': card, 'checkbox': checkbox, 'status': status_label,
            'content_btn': content_btn, 'word_lbl': word_label,
            'phonetic_lbl': phonetic_label, 'meaning_lbl': meaning_label,
            'play_btn': play_btn, 'delete_btn': delete_btn,
            'actions_frame': actions_frame
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
            status_text, bg_color = "掌握", ("#E8F5E9", "#1B5E20")
            text_color = ("#2E7D32", "#A5D6A7")
        elif next_time == 0:
            status_text, bg_color = "新词", ("#F5F5F5", "#424242")
            text_color = ("#616161", "#BDBDBD")
        elif next_time <= now_ts:
            status_text, bg_color = "到期", ("#FFEBEE", "#B71C1C")
            text_color = ("#C62828", "#EF9A9A")
        else:
            status_text, bg_color = "学习", ("#E3F2FD", "#0D47A1")
            text_color = ("#1565C0", "#90CAF9")

        row['status'].configure(
            text=f"{status_text} Lv.{stage}", 
            fg_color=bg_color, 
            text_color=text_color
        )

        # Update labels
        row['word_lbl'].configure(text=item['word'])

        phonetic = item.get('phonetic', '')
        tags = item.get('tags', '')
        if tags and len(tags) > 20:
            tags = tags[:17] + "..."

        phonetic_text = f"/{phonetic}/  [{tags}]" if tags else f"/{phonetic}/" if phonetic else ""
        row['phonetic_lbl'].configure(text=phonetic_text)

        # Meaning truncation & formatting (Multiline Support)
        meaning = item.get('meaning', '').strip()
        meaning = re.sub(r'\n+', '\n', meaning) # Collapse multiple newlines
        lines = meaning.split('\n')
        if len(lines) > 3:
            meaning = '\n'.join(lines[:3]).strip() + "..."
        elif len(meaning) > 200: # Character limit safeguard
            meaning = meaning[:197] + "..."
            
        row['meaning_lbl'].configure(text=meaning)

        # Setup click handlers: single click = focus, double click = open detail
        def on_row_single_click(e, x=item):
            # Find this item's index in current page
            start_idx = (self.current_page - 1) * self.page_size
            try:
                page_items = self.filtered_vocab_list[start_idx:start_idx + self.page_size]
                idx = page_items.index(x)
                self._on_row_click_focus(idx)
            except (ValueError, IndexError):
                pass
            return "break"
        
        def on_row_double_click(e, x=item):
            self.view_word_detail(x)
            return "break"

        # Apply recursive binding for clicks
        self._bind_click(row['content_btn'], on_row_single_click, on_row_double_click)

        # Bind right click (pass row for visual feedback)
        for widget in [row['content_btn'], row['word_lbl'], row['phonetic_lbl'], row['meaning_lbl']]:
            widget.bind("<Button-3>", lambda e, x=item, r=row: self.show_context_menu(e, x, r))
            widget.bind("<Button-2>", lambda e, x=item, r=row: self.show_context_menu(e, x, r))

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
        
        # Debounce: prevent multiple windows from opening on rapid clicks
        now = time.time()
        if now - self._last_detail_open_time < 0.6: # 600ms threshold
            return
        self._last_detail_open_time = now
        
        # Pass the current filtered list and the index of this item
        try:
            current_index = self.filtered_vocab_list.index(item)
            items_list = self.filtered_vocab_list
        except (AttributeError, ValueError):
            # Fallback if list not found or item not in current filter
            items_list = [item]
            current_index = 0
            
        DetailWindow(self.controller, item, self.controller, items_list=items_list, current_index=current_index)

    def delete_word(self, word):
        if messagebox.askyesno("删除确认", f"确定要删除单词 \"{word}\" 吗？\n\n此操作不可撤销。"):
            self.controller.db.delete_word(word)
            if word in self.selected_words:
                self.selected_words.remove(word)
            self.refresh_list()

    # --- Context Menu ---
    def show_context_menu(self, event, item, row=None):
        self.current_context_item = item
        self.current_context_row = row

        # Highlight the row to show which item is being acted upon
        if row:
            row['frame'].configure(border_color=("#3B8ED0", "#1f538d"), fg_color=("gray98", "#323232"))

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_context_menu_close(self, event=None):
        """Restore row style when context menu closes"""
        if self.current_context_row:
            self.current_context_row['frame'].configure(
                border_color=("gray90", "gray30"),
                fg_color=("white", "#2b2b2b")
            )
            self.current_context_row = None

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

    def sort_vocab_list(self, items, now_ts):
        def sort_key(item):
            if item.get('mastered'): return (3, 0)
            next_time = item.get('next_review_time', 0)
            if next_time == 0: return (1, 0)
            elif next_time <= now_ts: return (0, next_time)
            else: return (2, next_time)
        return sorted(items, key=sort_key)

    def apply_filters(self):
        """
        使用数据库层搜索和状态过滤，避免内存中二次过滤，提升大词库性能。
        """
        query = self.search_query.lower().strip()
        now_ts = datetime.now().timestamp()

        # 映射 UI 状态到数据库层 status_filter
        status = self.status_filter
        status_filter = None
        mastered_filter = None

        if status == "已掌握":
            mastered_filter = True
        elif status == "待复习":
            status_filter = "due"
        elif status == "新单词":
            status_filter = "new"
        elif status == "学习中":
            status_filter = "learning"
        # "全部" 不设置任何过滤

        # 使用数据库搜索（完全在数据库层过滤，无需二次过滤）
        results, total_count = self.controller.db.search_words(
            keyword=query,
            mastered_filter=mastered_filter,
            status_filter=status_filter,
            limit=10000,  # 获取足够多的结果用于排序和分页
            offset=0
        )

        self.filtered_vocab_list = self.sort_vocab_list(results, now_ts)
        total_items = len(self.filtered_vocab_list)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        if self.current_page > self.total_pages: self.current_page = self.total_pages
        self.lbl_results_count.configure(text=f"找到 {total_items} 个单词")

    def render_current_page(self):
        for row in self.row_pool:
            row['frame'].pack_forget()

        # Reset focus when page content changes
        self.focused_index = -1

        if not self.filtered_vocab_list:
            for row in self.row_pool: row['frame'].pack_forget()
            if self.row_pool:
                empty_row = self.row_pool[0]
                empty_row['checkbox'].grid_forget()
                empty_row['status'].master.grid_forget()
                empty_row['actions_frame'].grid_forget()
                empty_row['status'].configure(text="", fg_color="transparent")
                empty_row['frame'].configure(border_width=0, fg_color="transparent")
                empty_row['frame'].pack(fill="x", pady=100)
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
            row['frame'].configure(border_width=1, fg_color=("white", "#2b2b2b")) 
            row['checkbox'].grid(row=0, column=0, padx=(15, 10), sticky="w")
            row['status'].master.grid(row=0, column=0, sticky="ew")
            row['actions_frame'].grid(row=0, column=2, padx=(5, 15), sticky="e")
            self.update_row_widget(row, item, now_ts)
            row['frame'].pack(fill="x", pady=6, padx=15)
            # Bind click to focus this view for keyboard navigation
            row['frame'].bind("<Button-1>", lambda e, idx=i: self._on_row_click_focus(idx), add="+")

        try:
            self.list_scroll._parent_canvas.yview_moveto(0)
        except (AttributeError, Exception):
            pass

    def _on_row_click_focus(self, row_index):
        """Set focus to this view and update focused row index on click"""
        self.focus_set()
        self.focused_index = row_index
        self._update_focus_highlight()

    def update_pagination_controls(self):
        self.lbl_page_info.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        
        # Primary color for active, gray for disabled
        btn_color = ("#3B8ED0", "#1f538d")
        
        if self.current_page > 1:
            self.btn_prev.configure(state="normal", fg_color=btn_color)
        else:
            self.btn_prev.configure(state="disabled", fg_color=("gray90", "gray30"))
            
        if self.current_page < self.total_pages:
            self.btn_next.configure(state="normal", fg_color=btn_color)
        else:
            self.btn_next.configure(state="disabled", fg_color=("gray90", "gray30"))

    def go_prev_page(self):
        self._change_page(-1)

    def go_next_page(self):
        self._change_page(1)

    def _change_page(self, delta):
        """Navigate pages by delta (-1 or +1)"""
        new_page = self.current_page + delta
        if 1 <= new_page <= self.total_pages:
            self.current_page = new_page
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
