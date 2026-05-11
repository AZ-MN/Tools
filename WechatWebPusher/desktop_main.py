import socket
import shutil
import time

import webview

from backend.main import RUNTIME_ROOT, start_server

WINDOW_TITLE = ""
WINDOW_MIN_SIZE = (1240, 900)
WINDOW_SIZE = (1460, 980)
HOST = "127.0.0.1"
WINDOW_CHROME_COLOR = "#F4F8FC"
WINDOW_TEXT_COLOR = "#F4F8FC"


def wait_for_server(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError("本地服务启动超时，请稍后重试。")


def create_main_window(host: str, port: int):
    return webview.create_window(
        WINDOW_TITLE,
        f"http://{host}:{port}",
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=WINDOW_MIN_SIZE,
        resizable=True,
        background_color=WINDOW_CHROME_COLOR,
        text_select=True,
    )


def _hex_to_colorref(hex_color: str) -> int:
    color = hex_color.lstrip("#")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return (blue << 16) | (green << 8) | red


def _center_native_window(native_window) -> None:
    try:
        native_window.CenterToScreen()
        return
    except Exception:
        pass


def _enable_center_on_show(native_window) -> None:
    try:
        from System.Windows.Forms import FormStartPosition

        native_window.StartPosition = FormStartPosition.CenterScreen
    except Exception:
        pass

    shown_handler = None

    def handle_shown(*_args) -> None:
        try:
            _center_native_window(native_window)
        finally:
            try:
                native_window.Shown -= shown_handler
            except Exception:
                pass

    shown_handler = handle_shown

    try:
        native_window.Shown += shown_handler
    except Exception:
        _center_native_window(native_window)

    try:
        from System.Drawing import Point
        from System.Windows.Forms import Screen

        working_area = Screen.FromHandle(native_window.Handle).WorkingArea
        window_size = native_window.Size
        offset_x = max(working_area.X, working_area.X + (working_area.Width - window_size.Width) // 2)
        offset_y = max(working_area.Y, working_area.Y + (working_area.Height - window_size.Height) // 2)
        native_window.Location = Point(offset_x, offset_y)
    except Exception:
        pass


def configure_native_window(window) -> None:
    native_window = getattr(window, "native", None)
    if native_window is None:
        return

    try:
        native_window.MinimumSize = native_window.SizeFromClientSize(native_window.MinimumSize)
    except Exception:
        pass

    try:
        native_window.Text = ""
    except Exception:
        pass

    try:
        native_window.ShowIcon = False
    except Exception:
        pass

    _enable_center_on_show(native_window)

    try:
        import ctypes
        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        hwnd = int(native_window.Handle)
        border_color = ctypes.c_int(_hex_to_colorref(WINDOW_CHROME_COLOR))
        caption_color = ctypes.c_int(_hex_to_colorref(WINDOW_CHROME_COLOR))
        text_color = ctypes.c_int(_hex_to_colorref(WINDOW_TEXT_COLOR))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_BORDER_COLOR,
            ctypes.byref(border_color),
            ctypes.sizeof(border_color),
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(caption_color),
            ctypes.sizeof(caption_color),
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_TEXT_COLOR,
            ctypes.byref(text_color),
            ctypes.sizeof(text_color),
        )
    except Exception:
        pass


def main() -> None:
    server, server_thread, port = start_server(host=HOST, open_browser_on_start=False)
    wait_for_server(HOST, port)

    window = create_main_window(HOST, port)

    def shutdown() -> None:
        server.should_exit = True
        server.force_exit = True
        server_thread.join(timeout=5)

    window.events.closed += shutdown

    storage_dir = RUNTIME_ROOT / "webview_storage"
    shutil.rmtree(storage_dir, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    webview.start(configure_native_window, window, gui="edgechromium", debug=False, private_mode=False, storage_path=str(storage_dir))


if __name__ == "__main__":
    main()