@echo off
echo 正在安装打包工具...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo 正在打包中，这可能需要几分钟...
echo 请耐心等待，不要关闭窗口...

pyinstaller --noconfirm --clean MyVocabBook.spec

echo.
echo ==========================================
echo 打包完成！
echo 请在 dist 文件夹中找到 "我的生词本.exe"
echo ==========================================
pause