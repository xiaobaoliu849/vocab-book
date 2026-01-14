@echo off
cd /d "%~dp0"
:: 使用 pythonw 启动，不会弹出黑窗口
start "" pythonw app.pyw
exit