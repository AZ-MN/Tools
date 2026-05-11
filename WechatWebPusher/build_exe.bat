@echo off
setlocal
cd /d "%~dp0"

set DIST_DIR=dist_desktop
set BUILD_DIR=build_desktop
set APP_DIR=%DIST_DIR%\消息推送工作台
set LEGACY_APP_DIR=%DIST_DIR%\企微消息工作台

if exist "%LEGACY_APP_DIR%" (
  echo 正在清理旧版产物目录...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '%LEGACY_APP_DIR%') { Remove-Item -LiteralPath '%LEGACY_APP_DIR%' -Recurse -Force }"
)

echo 正在重新构建前端产物...
pushd frontend
call npm run build
if errorlevel 1 (
  echo 前端构建失败，请检查 Node.js 与依赖安装状态。
  popd
  exit /b 1
)
popd

if not exist "..\.venv\Scripts\python.exe" (
  echo 未检测到 Python 虚拟环境，请先创建 .venv 并安装依赖。
  exit /b 1
)

call "..\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --distpath "%DIST_DIR%" --workpath "%BUILD_DIR%" wechat_web_pusher.spec
if errorlevel 1 (
  echo 打包失败，请检查依赖安装状态和 spec 配置。
  exit /b 1
)

echo.
echo 打包完成，输出目录：%cd%\%APP_DIR%
endlocal