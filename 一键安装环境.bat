@echo off
cd /d "%~dp0"
echo [Step 1] Installing libraries...
echo Please wait...

py -m pip install customtkinter requests beautifulsoup4 keyboard pygame packaging -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo 'py' failed. Trying 'python'...
    python -m pip install customtkinter requests beautifulsoup4 keyboard pygame packaging -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo [Step 2] Installation Complete!
pause
