@echo off
cd /d "%~dp0"
echo 正在启动企微消息推送系统...
call ..\.venv\Scripts\activate.bat

for /f %%p in ('powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess)"') do (
	echo 检测到 8000 端口已被进程 %%p 占用，正在释放旧服务...
	taskkill /PID %%p /F >nul 2>nul
)

if not exist "frontend\dist\index.html" (
	echo 未检测到前端构建产物，正在执行 npm run build...
	pushd frontend
	call npm run build
	if errorlevel 1 (
		echo 前端构建失败，请检查 Node.js 与依赖安装状态。
		popd
		pause
		exit /b 1
	)
	popd
)

python backend\main.py
pause