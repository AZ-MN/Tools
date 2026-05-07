# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path.cwd()
frontend_dist = project_root / "frontend" / "dist"
icon_file = project_root / "frontend" / "public" / "bitbug_favicon.ico"

datas = [
    (str(frontend_dist), "frontend/dist"),
]
datas += collect_data_files("webview")


a = Analysis(
    [str(project_root / "desktop_main.py")],
    pathex=[str(project_root), str(project_root / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "pythonnet",
    ] + collect_submodules("webview"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="企微消息工作台",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_file) if icon_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="企微消息工作台",
)