# -*- mode: python ; coding: utf-8 -*-
"""
智能生词本 - 轻量版打包配置
"""

from PyInstaller.utils.hooks import collect_all

datas = [
    ('version.json', '.'),
    ('config.json', '.'),
    ('app.ico', '.'),
    ('app.png', '.'),
    ('donate_qr.png', '.'),
]

binaries = []
hiddenimports = []

# 收集 customtkinter 相关资源
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 添加必要的 hidden imports
hiddenimports.extend([
    'sqlite3',
    'ctypes',
    'ctypes.wintypes',
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.colorchooser',
    'tkinter.commondialog',
    'customtkinter',
    'customtkinter.windows',
    'customtkinter.windows.widgets',
    'customtkinter.windows.theme',
    'requests',
    'requests.utils',
    'requests.structures',
    'keyboard',
    'keyboard._nixKeyboard',
    'keyboard._nixCommon',
    'keyboard._win32',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'win10toast',
    'win10toast_click',
    'pystray',
    'pystray._win32',
    'pystray._util',
    'win32api',
    'win32con',
    'win32gui',
])

a = Analysis(
    ['vocab_app/main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy', 'pandas', 'matplotlib', 'scipy', 'IPython',
        'notebook', 'pytest', 'unittest', 'pydoc',
        'test', 'doctest', 'pdb',
        'lxml', 'lxml.etree', 'lxml.objectify',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'vcruntime140_1.dll'],
    name='MyVocabBook',
    icon='app.ico',
    debug=False,
    bootloader_ignore_signals=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
