@echo off
echo ==========================================
echo Starting Clean Build Process to Reduce Size
echo ==========================================

echo [1/5] Creating temporary virtual environment...
python -m venv venv_build

echo [2/5] Activating virtual environment...
call venv_build\Scripts\activate

echo [3/5] Installing minimal dependencies...
pip install -r requirements.txt
:: Uninstall numpy if it got pulled in (common source of bloat) unless strictly needed
pip uninstall -y numpy pandas matplotlib scipy

echo [4/5] Building executable...
pyinstaller --noconfirm --clean MyVocabBook.spec

echo [5/5] Cleanup...
deactivate
rmdir /s /q venv_build

echo.
echo ==========================================
echo Build Complete! Check dist/ folder.
echo ==========================================
pause