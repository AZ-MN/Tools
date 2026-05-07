# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['calculator.py'],
    pathex=[],
    binaries=[],
    # 特别注意这一行，确保包含图标文件
    datas=[('calculator.ico', '.')],  # 包含图标文件到最终打包目录
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='计算器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用UPX压缩可执行文件以减小体积
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 特别注意：这里是主程序图标（显示在任务栏/标题栏）
    icon=os.path.join(os.getcwd(), 'calculator.ico'),  # 确保提供绝对路径
)