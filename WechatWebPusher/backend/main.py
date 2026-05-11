import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import hmac
import json
import mimetypes
import os
import socket
import sys
import tempfile
import time
import urllib.parse
import uuid
import webbrowser
from pathlib import Path
from threading import Thread
from typing import Any, List, Literal

import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field
from requests import RequestException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import InvalidSchema, InvalidURL, MissingSchema, Timeout


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
SUPPORTED_PLATFORMS = {"qywx", "dingtalk", "feishu"}
PLATFORM_LABELS = {
    "qywx": "企微",
    "dingtalk": "钉钉",
    "feishu": "飞书",
}


class Webhook(BaseModel):
    name: str
    url: str
    platform: Literal["qywx", "dingtalk", "feishu"] = "qywx"
    app_id: str = ""
    app_secret: str = ""
    sign_secret: str = ""


class WebhookTestPayload(BaseModel):
    url: str
    platform: Literal["qywx", "dingtalk", "feishu"] = "qywx"
    app_id: str = ""
    app_secret: str = ""
    sign_secret: str = ""


class SendContent(BaseModel):
    text: str = ""
    upload_tokens: List[str] = Field(default_factory=list)


class SendMessageReq(BaseModel):
    webhook_names: List[str]
    msg_type: str
    content: SendContent


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


def looks_like_qywx_webhook_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=")


def looks_like_dingtalk_webhook_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith("https://oapi.dingtalk.com/robot/send?access_token=")


def looks_like_feishu_webhook_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/")


def guess_platform_from_url(value: str) -> str:
    if looks_like_qywx_webhook_url(value):
        return "qywx"
    if looks_like_dingtalk_webhook_url(value):
        return "dingtalk"
    if looks_like_feishu_webhook_url(value):
        return "feishu"
    return "qywx"


def validate_webhook_url(platform: str, value: str) -> None:
    trimmed_value = str(value).strip()
    platform_label = get_platform_label(platform)

    if not trimmed_value:
        raise HTTPException(status_code=400, detail="机器人名称、平台和地址不能为空")

    validators = {
        "qywx": looks_like_qywx_webhook_url,
        "dingtalk": looks_like_dingtalk_webhook_url,
        "feishu": looks_like_feishu_webhook_url,
    }

    validator = validators.get(platform)
    if validator and not validator(trimmed_value):
        raise HTTPException(status_code=400, detail=f"{platform_label}机器人地址格式不正确，请粘贴完整 Webhook 地址")


def normalize_webhooks(data: dict[str, Any]) -> tuple[dict[str, dict[str, str]], bool]:
    normalized: dict[str, dict[str, str]] = {}
    changed = False

    for key, value in data.items():
        if isinstance(value, dict):
            name = str(key).strip()
            url = str(value.get("url", "")).strip()
            platform = str(value.get("platform") or guess_platform_from_url(url)).strip().lower()
            if platform not in SUPPORTED_PLATFORMS:
                platform = guess_platform_from_url(url)
                changed = True

            normalized[name] = {
                "url": url,
                "platform": platform,
                "app_id": str(value.get("app_id", "")).strip(),
                "app_secret": str(value.get("app_secret", "")).strip(),
                "sign_secret": str(value.get("sign_secret", "")).strip(),
            }
            continue

        if looks_like_qywx_webhook_url(key) and not looks_like_qywx_webhook_url(value):
            normalized[str(value).strip()] = {"url": str(key).strip(), "platform": "qywx", "app_id": "", "app_secret": "", "sign_secret": ""}
            changed = True
            continue

        url = str(value).strip()
        normalized[str(key).strip()] = {
            "url": url,
            "platform": guess_platform_from_url(url),
            "app_id": "",
            "app_secret": "",
            "sign_secret": "",
        }
        changed = True

    return normalized, changed


def load_webhooks() -> dict[str, dict[str, str]]:
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


def save_webhooks(data: dict[str, dict[str, str]]) -> None:
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


def validate_public_image_url(image_url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed_url = urllib.parse.urlparse(str(image_url or "").strip())
    hostname = (parsed_url.hostname or "").lower()

    if parsed_url.scheme != "https" or not hostname:
        raise HTTPException(status_code=502, detail="公网图链返回了不安全的地址，请稍后重试。")

    if allowed_hosts and not any(hostname == host or hostname.endswith(f".{host}") for host in allowed_hosts):
        raise HTTPException(status_code=502, detail="公网图链返回了非预期域名，请稍后重试。")

    return parsed_url.geturl()


def prepare_public_upload_image(image_path: Path) -> tuple[Path, list[Path]]:
    cleanup_paths: list[Path] = []
    source_path = compress_image(image_path)
    if source_path != image_path:
        cleanup_paths.append(source_path)

    with Image.open(source_path) as image:
        if getattr(image, "is_animated", False):
            image.seek(0)

        has_alpha = "A" in image.getbands() or "transparency" in image.info
        sanitized = image.convert("RGBA" if has_alpha else "RGB")

        max_dimension = 2048
        if max(sanitized.size) > max_dimension:
            resize_ratio = max_dimension / max(sanitized.size)
            resized_width = max(200, int(sanitized.width * resize_ratio))
            resized_height = max(200, int(sanitized.height * resize_ratio))
            resample = getattr(Image, "Resampling", Image).LANCZOS
            sanitized = sanitized.resize((resized_width, resized_height), resample)

        suffix = ".png" if has_alpha else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, prefix="public-upload-", suffix=suffix) as temp_file:
            prepared_path = Path(temp_file.name)

        save_kwargs = {"optimize": True}
        if suffix == ".jpg":
            save_kwargs["quality"] = 82
            save_kwargs["progressive"] = True

        sanitized.save(prepared_path, **save_kwargs)

    final_path = compress_image(prepared_path)
    cleanup_paths.append(prepared_path)
    if final_path != prepared_path:
        cleanup_paths.append(final_path)

    return final_path, cleanup_paths


def upload_image_to_imgbed(image_path: Path) -> str:
    prepared_path, cleanup_paths = prepare_public_upload_image(image_path)
    try:
        with prepared_path.open("rb") as file:
            image_data = file.read()

        mime_type, _ = mimetypes.guess_type(str(prepared_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        files = {
            "file": (prepared_path.name, image_data, mime_type),
        }
        data = {
            "fileName": prepared_path.name,
            "uid": "3dfd757677824cecadcd7640baeb787d",
        }
        headers = {
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0",
        }

        response = requests.post("https://imgbed.cn/img/upload", files=files, data=data, headers=headers, timeout=40)
        response.raise_for_status()
        result = response.json()
        image_url = result.get("url")
        if not image_url:
            raise HTTPException(status_code=502, detail="图床上传失败，请稍后重试。")
        return validate_public_image_url(str(image_url), ("imgbed.cn",))
    finally:
        cleanup_uploads(cleanup_paths)


def upload_image_to_uguu(image_path: Path) -> str:
    prepared_path, cleanup_paths = prepare_public_upload_image(image_path)
    try:
        mime_type, _ = mimetypes.guess_type(str(prepared_path))
        with prepared_path.open("rb") as file:
            response = requests.post(
                "https://uguu.se/upload.php",
                files={"files[]": (prepared_path.name, file, mime_type or "application/octet-stream")},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=40,
            )

        response.raise_for_status()
        result = response.json()
        file_items = result.get("files") or []
        if not result.get("success") or not file_items:
            raise HTTPException(status_code=502, detail="公网图链上传失败，请稍后重试。")

        image_url = file_items[0].get("url")
        if not image_url:
            raise HTTPException(status_code=502, detail="公网图链上传失败，请稍后重试。")
        return validate_public_image_url(str(image_url), ("uguu.se",))
    finally:
        cleanup_uploads(cleanup_paths)


def upload_image_to_free_host(image_path: Path) -> str:
    uploaders = [upload_image_to_uguu, upload_image_to_imgbed]
    errors: list[str] = []

    for uploader in uploaders:
        try:
            return uploader(image_path)
        except HTTPException as error:
            errors.append(str(error.detail))
        except RequestException as error:
            errors.append(str(error))

    detail = errors[0] if errors else "公网图链上传失败，请稍后重试。"
    raise HTTPException(status_code=502, detail=f"钉钉图片上传失败：{detail}")


def get_feishu_tenant_access_token(app_id: str, app_secret: str) -> str:
    if not app_id.strip() or not app_secret.strip():
        raise HTTPException(status_code=400, detail="飞书发送本地图片需要先配置 App ID 和 App Secret。")

    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id.strip(), "app_secret": app_secret.strip()},
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"飞书凭证不可用：{result.get('msg') or '获取租户令牌失败'}")

    tenant_access_token = result.get("tenant_access_token")
    if not tenant_access_token:
        raise HTTPException(status_code=502, detail="飞书凭证不可用：未获取到租户令牌")
    return str(tenant_access_token)


def upload_image_to_feishu(image_path: Path, app_id: str, app_secret: str) -> str:
    tenant_access_token = get_feishu_tenant_access_token(app_id, app_secret)
    compressed_path = compress_image(image_path)
    with compressed_path.open("rb") as image_file:
        files = {"image": (compressed_path.name, image_file, mimetypes.guess_type(str(compressed_path))[0] or "application/octet-stream")}
        data = {"image_type": "message"}
        response = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {tenant_access_token}"},
            files=files,
            data=data,
            timeout=40,
        )

    response.raise_for_status()
    result = response.json()
    if result.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"飞书图片上传失败：{result.get('msg') or '上传失败'}")

    image_key = result.get("data", {}).get("image_key")
    if not image_key:
        raise HTTPException(status_code=502, detail="飞书图片上传失败：未返回 image_key")
    return str(image_key)


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


def post_payload_qywx(webhook_url: str, payload: dict[str, Any]) -> None:
    response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if result.get("errcode") != 0:
        raise HTTPException(status_code=502, detail=f"企微接口错误：{result.get('errmsg')}（错误码：{result.get('errcode')}）")


def build_dingtalk_signed_webhook_url(webhook_url: str, sign_secret: str = "") -> str:
    trimmed_secret = str(sign_secret or "").strip()
    if not trimmed_secret:
        return webhook_url

    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{trimmed_secret}"
    sign = base64.b64encode(
        hmac.new(trimmed_secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    encoded_sign = urllib.parse.quote_plus(sign)
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={encoded_sign}"


def post_payload_dingtalk(webhook_url: str, payload: dict[str, Any], sign_secret: str = "") -> None:
    signed_webhook_url = build_dingtalk_signed_webhook_url(webhook_url, sign_secret)
    response = requests.post(signed_webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if str(result.get("errcode", "0")) != "0":
        raise HTTPException(status_code=502, detail=f"钉钉接口错误：{result.get('errmsg') or '发送失败'}")


def post_payload_feishu(webhook_url: str, payload: dict[str, Any]) -> None:
    response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json; charset=utf-8"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if result.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"飞书接口错误：{result.get('msg') or result.get('message') or '发送失败'}")


def post_payload(platform: str, webhook_url: str, payload: dict[str, Any], webhook: dict[str, str] | None = None) -> None:
    if platform == "qywx":
        post_payload_qywx(webhook_url, payload)
        return
    if platform == "dingtalk":
        post_payload_dingtalk(webhook_url, payload, (webhook or {}).get("sign_secret", ""))
        return
    if platform == "feishu":
        post_payload_feishu(webhook_url, payload)
        return
    raise HTTPException(status_code=400, detail=f"暂不支持的平台：{platform}")


def format_webhook_error(platform: str, error: Exception) -> str:
    platform_label = get_platform_label(platform)

    if isinstance(error, HTTPException):
        return str(error.detail)

    if isinstance(error, (MissingSchema, InvalidSchema, InvalidURL)):
        return f"{platform_label}机器人地址无效，请在“编辑机器人”中粘贴完整 Webhook 地址。"

    if isinstance(error, Timeout):
        return f"连接{platform_label}超时，请检查网络后重试。"

    if isinstance(error, RequestsConnectionError):
        return f"无法连接到{platform_label}服务器，请检查网络或确认该机器人地址仍可用。"

    if isinstance(error, RequestException):
        return f"发送到{platform_label}失败，请检查机器人地址是否正确，或稍后重试。"

    return str(error) or error.__class__.__name__


def extract_title_from_markdown(content: str, fallback: str = "消息通知") -> str:
    for line in content.splitlines():
        trimmed = line.strip().lstrip("#").strip()
        if trimmed:
            return trimmed[:60]
    return fallback


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


def build_markdown_bundle_qywx(content: str, upload_paths: List[Path]) -> dict[str, Any]:
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


def build_image_bundle_qywx(upload_paths: List[Path]) -> dict[str, Any]:
    if not upload_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张图片。")
    image_payloads = [build_image_payload(path) for path in upload_paths]
    return {"primary": None, "extra_images": image_payloads, "notes": []}


def build_markdown_bundle_dingtalk(content: str, upload_paths: List[Path]) -> dict[str, Any]:
    markdown_content = content.strip()
    if not markdown_content and not upload_paths:
        raise HTTPException(status_code=400, detail="请输入要发送的 Markdown 内容。")

    embedded_image_urls = [upload_image_to_free_host(path) for path in upload_paths]
    message_body = markdown_content or "### 图片通知"

    for index, image_url in enumerate(embedded_image_urls, start=1):
        message_body += f"\n\n![图片{index}]({image_url})"

    return {
        "primary": {
            "msgtype": "markdown",
            "markdown": {
                "title": extract_title_from_markdown(message_body, "钉钉通知"),
                "text": message_body,
            },
        },
        "extra_images": [],
        "notes": [],
    }


def build_markdown_bundle_feishu(content: str, upload_paths: List[Path], webhook: dict[str, str]) -> dict[str, Any]:
    markdown_content = content.strip()
    if not markdown_content and not upload_paths:
        raise HTTPException(status_code=400, detail="请输入要发送的 Markdown 内容或上传至少一张图片。")

    if upload_paths:
        image_keys = [upload_image_to_feishu(path, webhook.get("app_id", ""), webhook.get("app_secret", "")) for path in upload_paths]
        post_lines: list[list[dict[str, Any]]] = []

        for line in markdown_content.splitlines():
            trimmed = line.strip()
            if trimmed:
                post_lines.append([{"tag": "text", "text": trimmed}])

        for image_key in image_keys:
            post_lines.append([{"tag": "img", "image_key": image_key}])

        return {
            "primary": {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh-CN": {
                            "title": extract_title_from_markdown(markdown_content, "飞书通知"),
                            "content": post_lines or [[{"tag": "text", "text": "图片通知"}]],
                        }
                    }
                },
            },
            "extra_images": [],
            "notes": [],
        }

    title = extract_title_from_markdown(markdown_content, "飞书通知")
    return {
        "primary": {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"content": title, "tag": "plain_text"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": markdown_content,
                        },
                    }
                ],
            },
        },
        "extra_images": [],
        "notes": [],
    }


def build_image_bundle_dingtalk(upload_paths: List[Path]) -> dict[str, Any]:
    if not upload_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张图片。")
    return build_markdown_bundle_dingtalk("", upload_paths)


def build_image_bundle_feishu(upload_paths: List[Path], webhook: dict[str, str]) -> dict[str, Any]:
    if not upload_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张图片。")
    return build_markdown_bundle_feishu("", upload_paths, webhook)


def build_test_payload(platform: str) -> dict[str, Any]:
    if platform == "qywx":
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": "# 连接测试\n这是一条来自消息推送工作台的测试消息。",
            },
        }

    if platform == "dingtalk":
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "连接测试",
                "text": "### 连接测试\n这是一条来自消息推送工作台的测试消息。",
            },
        }

    if platform == "feishu":
        return {
            "msg_type": "text",
            "content": {
                "text": "连接测试：这是一条来自消息推送工作台的测试消息。",
            },
        }

    raise HTTPException(status_code=400, detail=f"暂不支持的平台：{platform}")


def build_message_bundle(req: SendMessageReq, upload_paths: List[Path], webhook: dict[str, str]) -> dict[str, Any]:
    platform = webhook.get("platform", "qywx")
    if req.msg_type == "markdown":
        if platform == "qywx":
            return build_markdown_bundle_qywx(req.content.text, upload_paths)
        if platform == "dingtalk":
            return build_markdown_bundle_dingtalk(req.content.text, upload_paths)
        if platform == "feishu":
            return build_markdown_bundle_feishu(req.content.text, upload_paths, webhook)
    if req.msg_type == "image":
        if platform == "qywx":
            return build_image_bundle_qywx(upload_paths)
        if platform == "dingtalk":
            return build_image_bundle_dingtalk(upload_paths)
        if platform == "feishu":
            return build_image_bundle_feishu(upload_paths, webhook)
    raise HTTPException(status_code=400, detail=f"暂不支持的消息类型：{req.msg_type}")


def build_bundle_cache_key(webhook: dict[str, str]) -> tuple[str, str, str]:
    platform = webhook.get("platform", "qywx")
    if platform == "feishu":
        return (platform, webhook.get("app_id", "").strip(), webhook.get("app_secret", "").strip())
    return (platform, "", "")


def run_webhook_test(platform: str, webhook_url: str, webhook: dict[str, str] | None = None) -> dict[str, str]:
    validate_webhook_url(platform, webhook_url)

    try:
        post_payload(platform, webhook_url, build_test_payload(platform), webhook)
    except Exception as error:
        raise HTTPException(status_code=400, detail=format_webhook_error(platform, error)) from error

    return {"status": "success", "message": f"{get_platform_label(platform)}机器人连接正常"}


@app.get("/")
def redirect_to_index():
    return RedirectResponse(url="/index.html")


@app.get("/api/webhooks")
def get_webhooks():
    return load_webhooks()


@app.post("/api/webhooks")
def add_webhook(webhook: Webhook):
    if not webhook.name.strip() or not webhook.url.strip() or not webhook.platform.strip():
        raise HTTPException(status_code=400, detail="机器人名称、平台和地址不能为空")

    validate_webhook_url(webhook.platform, webhook.url)

    data = load_webhooks()
    data[webhook.name.strip()] = {
        "url": webhook.url.strip(),
        "platform": webhook.platform.strip(),
        "app_id": webhook.app_id.strip(),
        "app_secret": webhook.app_secret.strip(),
        "sign_secret": webhook.sign_secret.strip(),
    }
    save_webhooks(data)
    return {"status": "success"}


@app.put("/api/webhooks/{name}")
def update_webhook(name: str, webhook: Webhook):
    old_name = name.strip()
    new_name = webhook.name.strip()
    new_url = webhook.url.strip()
    new_platform = webhook.platform.strip()

    if not new_name or not new_url or not new_platform:
        raise HTTPException(status_code=400, detail="机器人名称、平台和地址不能为空")

    validate_webhook_url(new_platform, new_url)

    data = load_webhooks()
    if old_name not in data:
        raise HTTPException(status_code=404, detail="要编辑的机器人不存在")

    if new_name != old_name and new_name in data:
        raise HTTPException(status_code=400, detail="机器人名称已存在，请使用其他名称")

    del data[old_name]
    data[new_name] = {
        "url": new_url,
        "platform": new_platform,
        "app_id": webhook.app_id.strip(),
        "app_secret": webhook.app_secret.strip(),
        "sign_secret": webhook.sign_secret.strip(),
    }
    save_webhooks(data)
    return {"status": "success"}


@app.delete("/api/webhooks/{name}")
def delete_webhook(name: str):
    data = load_webhooks()
    if name in data:
        del data[name]
        save_webhooks(data)
    return {"status": "success"}


@app.post("/api/webhooks/{name}/test")
def test_webhook(name: str):
    data = load_webhooks()
    webhook = data.get(name)
    if not webhook:
        raise HTTPException(status_code=404, detail="要测试的机器人不存在")

    platform = webhook.get("platform", "qywx")
    webhook_url = webhook.get("url", "")
    return run_webhook_test(platform, webhook_url, webhook)


@app.post("/api/webhooks/test")
def test_webhook_draft(webhook: WebhookTestPayload):
    platform = webhook.platform.strip()
    webhook_url = webhook.url.strip()

    if not platform or not webhook_url:
        raise HTTPException(status_code=400, detail="请先填写平台和 Webhook 地址")

    return run_webhook_test(platform, webhook_url, {
        "platform": platform,
        "url": webhook_url,
        "app_id": webhook.app_id.strip(),
        "app_secret": webhook.app_secret.strip(),
        "sign_secret": webhook.sign_secret.strip(),
    })


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
    if not req.webhook_names:
        raise HTTPException(status_code=400, detail="请至少选择一个机器人。")

    webhooks = load_webhooks()
    upload_paths = resolve_upload_paths(req.content.upload_tokens)
    results = []
    notes: List[str] = []
    deliveries: list[tuple[str, dict[str, str], dict[str, Any]]] = []
    bundle_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    seen_notes: set[str] = set()

    try:
        for webhook_name in req.webhook_names:
            webhook = webhooks.get(webhook_name)
            if not webhook:
                results.append({"name": webhook_name, "status": "error", "msg": "机器人不存在或已被删除"})
                continue

            platform = webhook.get("platform", "qywx")
            try:
                cache_key = build_bundle_cache_key(webhook)
                bundle = bundle_cache.get(cache_key)
                if bundle is None:
                    bundle = build_message_bundle(req, upload_paths, webhook)
                    bundle_cache[cache_key] = bundle
                    for note in bundle.get("notes", []):
                        if note not in seen_notes:
                            seen_notes.add(note)
                            notes.append(note)

                deliveries.append((webhook_name, webhook, bundle))
            except Exception as error:
                message = format_webhook_error(platform, error)
                results.append({"name": webhook_name, "status": "error", "msg": message})

        def deliver_message(webhook_name: str, webhook: dict[str, str], bundle: dict[str, Any]) -> dict[str, str]:
            platform = webhook.get("platform", "qywx")
            webhook_url = webhook.get("url", "")
            if bundle.get("primary"):
                post_payload(platform, webhook_url, bundle["primary"], webhook)
            for image_payload in bundle.get("extra_images", []):
                post_payload(platform, webhook_url, image_payload, webhook)
            return {"name": webhook_name, "status": "success"}

        if deliveries:
            max_workers = min(8, len(deliveries))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(deliver_message, webhook_name, webhook, bundle): (webhook_name, webhook)
                    for webhook_name, webhook, bundle in deliveries
                }

                for future in as_completed(future_map):
                    webhook_name, webhook = future_map[future]
                    platform = webhook.get("platform", "qywx")
                    try:
                        results.append(future.result())
                    except Exception as error:
                        message = format_webhook_error(platform, error)
                        results.append({"name": webhook_name, "status": "error", "msg": message})
    finally:
        cleanup_uploads(upload_paths)

    return {"results": results, "notes": notes}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


if __name__ == "__main__":
    server, server_thread, _ = start_server(open_browser_on_start=True)
    server_thread.join()

