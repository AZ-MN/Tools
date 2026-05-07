# 企微消息工作台打包说明

## 输出形式

- PyInstaller 单目录桌面程序包
- 输出目录：WechatWebPusher/dist_desktop/企微消息工作台
- 主程序：WechatWebPusher/dist_desktop/企微消息工作台/企微消息工作台.exe

## 打包前提

- 已安装前端依赖
- 已安装 Python 依赖
- 已存在 .venv 虚拟环境

## 一键打包

在 WechatWebPusher 目录执行：

build_exe.bat

该脚本会：

- 检查并构建 frontend/dist
- 调用 PyInstaller 执行 wechat_web_pusher.spec
- 打包为内置桌面窗口运行模式，不再依赖系统默认浏览器打开页面

## 运行时目录

打包后的 exe 会把可写数据放到当前用户本机目录，而不是程序解压临时目录：

- 配置文件：%LOCALAPPDATA%\WechatWebPusher\config\webhooks_config.json
- 临时上传目录：%LOCALAPPDATA%\WechatWebPusher\temp_uploads
- WebView 缓存目录：%LOCALAPPDATA%\WechatWebPusher\webview_storage

这样做可以避免：

- 单文件或临时目录模式下配置丢失
- 无写权限目录导致启动失败
- 升级程序后临时上传目录失效

## 分发建议

- 直接分发整个 dist_desktop/企微消息工作台 目录
- 不要只拷贝 exe，旁边的依赖文件和静态资源必须一并保留

## 运行效果

- 双击 exe 后会直接打开本地桌面窗口
- 不会再自动拉起外部浏览器