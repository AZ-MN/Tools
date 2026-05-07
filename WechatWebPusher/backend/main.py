import base64
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
import uuid
import webbrowser
from pathlib import Path
from threading import Thread
from typing import Any, List

import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field


app = FastAPI(title="企微消息推送 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base_dir / "WechatWebPusher"
    return Path(__file__).resolve().parent.parent


RESOURCE_ROOT = get_resource_root()
RUNTIME_ROOT = get_runtime_root()
FRONTEND_DIST = RESOURCE_ROOT / "frontend" / "dist"
CONFIG_DIR = RUNTIME_ROOT / "config"
CONFIG_FILENAME = CONFIG_DIR / "webhooks_config.json"
UPLOAD_DIR = RUNTIME_ROOT / "temp_uploads"
MAX_IMAGE_SIZE_MB = 2
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class Webhook(BaseModel):
    name: str
    url: str


class SendContent(BaseModel):
    text: str = ""
    upload_tokens: List[str] = Field(default_factory=list)


class SendMessageReq(BaseModel):
    webhook_urls: List[str]
    msg_type: str
    content: SendContent


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def looks_like_webhook_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=")


def normalize_webhooks(data: dict[str, str]) -> tuple[dict[str, str], bool]:
    normalized: dict[str, str] = {}
    changed = False

    for key, value in data.items():
        if looks_like_webhook_url(key) and not looks_like_webhook_url(value):
            normalized[str(value).strip()] = str(key).strip()
            changed = True
            continue

        normalized[str(key).strip()] = str(value).strip()

    return normalized, changed


def load_webhooks() -> dict[str, str]:
    if CONFIG_FILENAME.exists():
        with CONFIG_FILENAME.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)
        if isinstance(raw_data, dict) and isinstance(raw_data.get("webhooks"), dict):
            raw_data = raw_data.get("webhooks", {})
        normalized, changed = normalize_webhooks(raw_data)
        if changed:
            save_webhooks(normalized)
        return normalized
    return {}


def save_webhooks(data: dict[str, str]) -> None:
    ensure_dirs()
    with CONFIG_FILENAME.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def build_image_payload(image_path: Path) -> dict[str, Any]:
    compressed_path = compress_image(image_path)
    try:
        with compressed_path.open("rb") as file:
            image_bytes = file.read()
    finally:
        if compressed_path != image_path:
            cleanup_uploads([compressed_path])
    return {
        "msgtype": "image",
        "image": {
            "base64": base64.b64encode(image_bytes).decode("utf-8"),
            "md5": hashlib.md5(image_bytes).hexdigest(),
        },
    }


def compress_image(image_path: Path, max_size_mb: int = MAX_IMAGE_SIZE_MB) -> Path:
    file_size_mb = image_path.stat().st_size / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return image_path

    with Image.open(image_path) as image:
        ratio = min(1.0, ((max_size_mb * 1024 * 1024) / max(image_path.stat().st_size, 1)) ** 0.5)
        width = max(200, int(image.width * ratio))
        height = max(200, int(image.height * ratio))
        resample = getattr(Image, "Resampling", Image).LANCZOS
        resized = image.resize((width, height), resample)
        suffix = image_path.suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)

        save_kwargs = {"optimize": True}
        if suffix.lower() in {".jpg", ".jpeg", ".webp"}:
            if resized.mode not in ("RGB", "L"):
                resized = resized.convert("RGB")
            save_kwargs["quality"] = 82
        resized.save(temp_path, **save_kwargs)
        return temp_path


def post_payload(webhook_url: str, payload: dict[str, Any]) -> None:
    response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if result.get("errcode") != 0:
        raise HTTPException(status_code=502, detail=f"企微接口错误：{result.get('errmsg')}（错误码：{result.get('errcode')}）")


def resolve_upload_token(token: str) -> Path:
    path = UPLOAD_DIR / token
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"上传文件不存在：{token}。该图片可能已被移除、发送后已清理，或服务重启后本地临时队列失效，请重新上传。")
    return path


def resolve_upload_paths(tokens: List[str]) -> List[Path]:
    return [resolve_upload_token(token) for token in tokens]


def cleanup_uploads(paths: List[Path]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def get_available_port(preferred_port: int = 8000) -> int:
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("未找到可用的本地监听端口，请关闭占用 8000-8019 端口的程序后重试。")


def create_server(host: str = "127.0.0.1", port: int | None = None) -> tuple[uvicorn.Server, Thread, int]:
    ensure_dirs()
    server_port = port or get_available_port()
    config = uvicorn.Config(app, host=host, port=server_port, log_config=None, access_log=False)
    server = uvicorn.Server(config)
    server_thread = Thread(target=server.run, daemon=True)
    return server, server_thread, server_port


def start_server(host: str = "127.0.0.1", port: int | None = None, open_browser_on_start: bool = False) -> tuple[uvicorn.Server, Thread, int]:
    server, server_thread, server_port = create_server(host=host, port=port)

    if open_browser_on_start:
        def open_browser() -> None:
            time.sleep(2)
            webbrowser.open(f"http://{host}:{server_port}")

        Thread(target=open_browser, daemon=True).start()

    server_thread.start()
    return server, server_thread, server_port


def build_markdown_bundle(content: str, upload_paths: List[Path]) -> dict[str, Any]:
    markdown_content = content.strip()
    extra_images: List[dict[str, Any]] = []
    notes: List[str] = []

    if not markdown_content and not upload_paths:
        raise HTTPException(status_code=400, detail="请输入 Markdown 内容或上传至少一张图片。")

    if upload_paths:
        extra_images = [build_image_payload(path) for path in upload_paths]
        notes.append("已上传的图片会在 Markdown 正文发送后逐张补发。")

    payload = {"msgtype": "markdown", "markdown": {"content": markdown_content or "图片已上传"}}
    return {"primary": payload, "extra_images": extra_images, "notes": notes}


def build_image_bundle(upload_paths: List[Path]) -> dict[str, Any]:
    if not upload_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张图片。")
    image_payloads = [build_image_payload(path) for path in upload_paths]
    return {"primary": None, "extra_images": image_payloads, "notes": []}


def build_message_bundle(req: SendMessageReq, upload_paths: List[Path]) -> dict[str, Any]:
    if req.msg_type == "markdown":
        return build_markdown_bundle(req.content.text, upload_paths)
    if req.msg_type == "image":
        return build_image_bundle(upload_paths)
    raise HTTPException(status_code=400, detail=f"暂不支持的消息类型：{req.msg_type}")


@app.get("/")
def redirect_to_index():
    return RedirectResponse(url="/index.html")


@app.get("/api/webhooks")
def get_webhooks():
    return load_webhooks()


@app.post("/api/webhooks")
def add_webhook(webhook: Webhook):
    if not webhook.name.strip() or not webhook.url.strip():
        raise HTTPException(status_code=400, detail="机器人名称和地址不能为空")

    data = load_webhooks()
    data[webhook.name.strip()] = webhook.url.strip()
    save_webhooks(data)
    return {"status": "success"}


@app.put("/api/webhooks/{name}")
def update_webhook(name: str, webhook: Webhook):
    old_name = name.strip()
    new_name = webhook.name.strip()
    new_url = webhook.url.strip()

    if not new_name or not new_url:
        raise HTTPException(status_code=400, detail="机器人名称和地址不能为空")

    data = load_webhooks()
    if old_name not in data:
        raise HTTPException(status_code=404, detail="要编辑的机器人不存在")

    if new_name != old_name and new_name in data:
        raise HTTPException(status_code=400, detail="机器人名称已存在，请使用其他名称")

    del data[old_name]
    data[new_name] = new_url
    save_webhooks(data)
    return {"status": "success"}


@app.delete("/api/webhooks/{name}")
def delete_webhook(name: str):
    data = load_webhooks()
    if name in data:
        del data[name]
        save_webhooks(data)
    return {"status": "success"}


@app.post("/api/upload_image")
async def upload_image(file: UploadFile = File(...)):
    ensure_dirs()
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in SUPPORTED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持常见图片格式上传。")

    token = f"{uuid.uuid4().hex}{suffix}"
    target_path = UPLOAD_DIR / token
    content = await file.read()
    with target_path.open("wb") as output:
        output.write(content)

    return {
        "token": token,
        "name": file.filename,
        "size": len(content),
        "uploaded_at": int(time.time()),
    }


@app.delete("/api/uploads/{token}")
def delete_uploaded_image(token: str):
    path = resolve_upload_token(token)
    cleanup_uploads([path])
    return {"status": "success"}


@app.post("/api/send")
def send_message(req: SendMessageReq):
    if not req.webhook_urls:
        raise HTTPException(status_code=400, detail="请至少选择一个机器人。")

    upload_paths = resolve_upload_paths(req.content.upload_tokens)
    results = []
    notes: List[str] = []

    try:
        bundle = build_message_bundle(req, upload_paths)
        notes.extend(bundle.get("notes", []))

        for webhook_url in req.webhook_urls:
            try:
                if bundle.get("primary"):
                    post_payload(webhook_url, bundle["primary"])
                for image_payload in bundle.get("extra_images", []):
                    post_payload(webhook_url, image_payload)
                results.append({"url": webhook_url, "status": "success"})
            except Exception as error:
                message = getattr(error, "detail", None) or str(error) or error.__class__.__name__
                results.append({"url": webhook_url, "status": "error", "msg": message})
    finally:
        cleanup_uploads(upload_paths)

    return {"results": results, "notes": notes}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


if __name__ == "__main__":
    server, server_thread, _ = start_server(open_browser_on_start=True)
    server_thread.join()

