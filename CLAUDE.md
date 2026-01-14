# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This is a Python-based desktop vocabulary learning application ("智能生词本") built with CustomTkinter. It features word lookup (Youdao API), spaced repetition review (SM-2), and vocabulary management.

## Architecture (v3.1 Modular)
The application has been refactored into a modular architecture.

- **Root**: `vocab_app/`
- **Entry Point**: `vocab_app/main.py` (VocabApp class)
- **Data Persistence**:
  - `vocab.db`: SQLite database (User Data)
  - `config.json`: Application settings
  - `sounds/`: Cached audio files
- **Modules**:
  - `models/`: Database interactions (`DatabaseManager`)
  - `views/`: UI Components (`AddView`, `ListView`, `ReviewView`, `SettingsView`, `DetailWindow`)
  - `services/`: Business Logic (`DictService`, `AudioService`, `ReviewService`, `ExportService`)
  - `config.py`: Configuration and Path management

## Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running the App
```bash
# Run the new modular version
python vocab_app/main.py
```

### Building
The project uses PyInstaller.
```bash
# Standard build
pyinstaller MyVocabBook.spec
```

## Code Style & Conventions
- **UI Threading**: Network requests must run in separate threads. Services are generally blocking; Views handle threading.
- **Path Handling**: Use `config.BASE_DIR` or `config.RESOURCE_DIR` to support both Dev and Frozen (EXE) modes.
- **Encoding**: Always use `utf-8` for text files.
