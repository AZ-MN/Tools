@echo off
setlocal
cd /d "%~dp0"

set DIST_DIR=dist_desktop
set BUILD_DIR=build_desktop

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

echo.
echo 打包完成，输出目录：%cd%\%DIST_DIR%\企微消息工作台
endlocal