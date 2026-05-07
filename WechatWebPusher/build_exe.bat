@echo off
setlocal
cd /d "%~dp0"

set DIST_DIR=dist_desktop
set BUILD_DIR=build_desktop
set APP_DIR=%DIST_DIR%\企微消息工作台
set ZIP_FILE=%DIST_DIR%\wechat_web_pusher_portable.zip

if not exist "frontend\dist\index.html" (
  echo 未检测到前端构建产物，正在执行 npm run build...
  pushd frontend
  call npm run build
  if errorlevel 1 (
    echo 前端构建失败，请检查 Node.js 与依赖安装状态。
    popd
    exit /b 1
  )
  popd
)

if not exist "..\.venv\Scripts\python.exe" (
  echo 未检测到 Python 虚拟环境，请先创建 .venv 并安装依赖。
  exit /b 1
)

call "..\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --distpath "%DIST_DIR%" --workpath "%BUILD_DIR%" wechat_web_pusher.spec
if errorlevel 1 (
  echo 打包失败，请检查依赖安装状态和 spec 配置。
  exit /b 1
)

call "..\.venv\Scripts\python.exe" -c "from pathlib import Path; import shutil; dist = Path(r'%DIST_DIR%'); app_dir = next((path for path in dist.iterdir() if path.is_dir()), None); assert app_dir is not None, 'package output directory not found'; zip_path = Path(r'%ZIP_FILE%'); zip_path.unlink(missing_ok=True); archive = Path(shutil.make_archive(str(zip_path.with_suffix('')), 'zip', root_dir=str(app_dir.parent), base_dir=app_dir.name)); print(archive.resolve())"
if errorlevel 1 (
  echo 生成分发压缩包失败，请检查 Python 环境与输出目录状态。
  exit /b 1
)

echo.
echo 打包完成，输出目录：%cd%\%APP_DIR%
echo 分发压缩包：%cd%\%ZIP_FILE%
endlocal