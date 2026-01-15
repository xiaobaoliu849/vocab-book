# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

智能生词本 (Smart Vocabulary Book) - A Windows desktop vocabulary learning application built with Python and CustomTkinter. Features include word lookup from multiple dictionaries, SM-2 spaced repetition algorithm for review, system tray integration, and auto-update capability.

## Commands

### Run the Application
```bash
py vocab_app/main.py
```

### Install Dependencies
```bash
py -m pip install -r requirements.txt
```

### Build Executable
```bash
pyinstaller MyVocabBook_Lite.spec
```
The spec file excludes large scientific computing libraries (numpy, pandas, etc.) to reduce size. Uses UPX compression. Output is a single-file Windows executable.

## Architecture

### Module Structure (MVC Pattern)

```
vocab_app/
├── main.py           # App entry point, VocabApp class (CTk main window)
├── config.py         # Config loading/saving, paths, theme setup
├── models/
│   └── database.py   # SQLite database manager (words, review_history, word_families tables)
├── views/            # UI views extending BaseView
│   ├── base_view.py  # Base class with audio playback helper
│   ├── add_view.py   # Word search and add interface
│   ├── list_view.py  # Word list with batch delete
│   ├── review_view.py # Flashcard/spelling review with SM-2 algorithm
│   ├── settings_view.py # Settings with sidebar navigation
│   └── close_dialog.py  # Close action chooser
└── services/         # Business logic services
    ├── dict_service.py       # Youdao dictionary scraping
    ├── multi_dict_service.py # Aggregated multi-source lookup (Bing, Cambridge, FreeDictionary)
    ├── audio_service.py      # TTS pronunciation via pygame
    ├── review_service.py     # SM-2 algorithm implementation
    ├── tray_service.py       # System tray icon (pystray)
    ├── notification_service.py # Windows toast notifications, review scheduler
    ├── update_service.py     # Auto-update via batch script replacement
    ├── export_service.py     # CSV import/export
    ├── tag_service.py        # Exam tags extraction (CET4, GRE, etc.)
    └── word_family_service.py # Derivative word grouping by root
```

### Key Patterns

- **View Controller**: `VocabApp` in main.py acts as controller, passed to views via `controller` parameter
- **View Lifecycle**: Views implement `setup_ui()` for initialization and `on_show()` for refresh logic
- **Database**: All DB access through `DatabaseManager`. Uses SQLite with connection-per-operation pattern
- **Threading**: Dictionary lookups and audio playback run in daemon threads to avoid UI blocking
- **Config**: JSON config at project root (`config.json`), loaded/saved via config.py

### Database Schema

**words** table: word, phonetic, meaning, example, roots, synonyms, tags, context_en/cn, date_added, SM-2 fields (easiness, interval, repetitions, next_review_time), review_count, mastered, stage

**review_history** table: For heatmap visualization, tracks word_id, review_date, rating

**word_families** table: Maps words to roots for derivative word grouping

### Windows-Specific Features
- Global hotkey (Ctrl+Alt+V default) via `keyboard` library
- System tray via `pystray`
- Notifications via `win10toast-click`
- SDL audio driver set to directsound for pygame

## Configuration

- `config.json`: User settings (theme, hotkey, close_action, reminder_interval, dict_sources)
- `version.json`: App version for update detection
