#!/usr/bin/env python3
"""
drpr MCP server — stdio transport.
Bundled with the drpr Claude Code plugin.
Tools: drpr_login, drpr_upload, drpr_status, drpr_logout
"""

import json
import sys
import os
import time
import uuid
import urllib.request
import urllib.error
import mimetypes
import io
import subprocess
import platform

DRPR_BASE = "https://drpr.host"
POLL_INTERVAL = 2
AUTH_TIMEOUT = 600


def send(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def text_result(req_id, text):
    send(ok(req_id, {"content": [{"type": "text", "text": text}]}))


def key_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = os.path.join(base, "drpr")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "api_key")


def load_key():
    try:
        with open(key_path()) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def save_key(key):
    p = key_path()
    with open(p, "w") as f:
        f.write(key)
    os.chmod(p, 0o600)


def delete_key():
    try:
        os.remove(key_path())
    except FileNotFoundError:
        pass


def open_browser(url):
    try:
        s = platform.system()
        if s == "Darwin":
            subprocess.Popen(["open", url])
        elif s == "Windows":
            subprocess.Popen(["cmd", "/c", "start", url])
        else:
            subprocess.Popen(["xdg-open", url])
        return True
    except Exception:
        return False


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def multipart_upload(file_path, subdomain, api_key):
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        data = f.read()

    boundary = uuid.uuid4().hex
    body = io.BytesIO()

    if subdomain:
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="subdomain"\r\n\r\n')
        body.write(f"{subdomain}\r\n".encode())

    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(data)
    body.write(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{DRPR_BASE}/api/v1/upload",
        data=body.getvalue(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def tool_login(args, req_id):
    existing = load_key()
    if existing and not args.get("force"):
        text_result(req_id, "already_authenticated")
        return

    device_token = uuid.uuid4().hex
    login_url = f"{DRPR_BASE}/cli-login?token={device_token}"
    poll_url = f"{DRPR_BASE}/api/cli/token/{device_token}"

    opened = open_browser(login_url)
    prefix = "browser_opened" if opened else "open_browser"
    text_result(req_id, f"{prefix}:{login_url}")

    deadline = time.time() + AUTH_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            data = get_json(poll_url)
            if data.get("api_key"):
                save_key(data["api_key"])
                text_result(req_id, f"authenticated:{data['api_key'][:8]}...")
                return
            if data.get("expired"):
                text_result(req_id, "error:login_expired")
                return
        except Exception:
            continue

    text_result(req_id, "error:login_timeout")


def tool_upload(args, req_id):
    file_path = args.get("file_path", "").strip()
    subdomain = args.get("subdomain", "").strip()

    if not file_path:
        text_result(req_id, "error:file_path required")
        return
    if not os.path.isfile(file_path):
        text_result(req_id, f"error:file not found: {file_path}")
        return

    api_key = load_key()
    if not api_key:
        text_result(req_id, "error:not_authenticated")
        return

    try:
        result = multipart_upload(file_path, subdomain, api_key)
        if result.get("url"):
            text_result(req_id, f"uploaded:{result['url']}")
        else:
            text_result(req_id, f"error:{json.dumps(result)}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 401:
            delete_key()
            text_result(req_id, "error:unauthorized")
        elif e.code == 409:
            text_result(req_id, f"error:http_409:{body}")
        else:
            text_result(req_id, f"error:http_{e.code}:{body}")
    except Exception as e:
        text_result(req_id, f"error:{str(e)}")


def tool_status(args, req_id):
    key = load_key()
    if not key:
        text_result(req_id, "not_authenticated")
        return
    try:
        data = get_json(
            f"{DRPR_BASE}/api/v1/me",
            headers={"Authorization": f"Bearer {key}"},
        )
        text_result(req_id, f"authenticated:{data.get('email', 'unknown')}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            delete_key()
            text_result(req_id, "not_authenticated:key_invalid")
        else:
            text_result(req_id, f"error:http_{e.code}")
    except Exception as e:
        text_result(req_id, f"error:{str(e)}")


def tool_logout(args, req_id):
    delete_key()
    text_result(req_id, "logged_out")


TOOLS = [
    {
        "name": "drpr_login",
        "description": "Authenticate with drpr.host. Opens browser and polls until complete. Pass force=true to re-authenticate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "description": "Force re-authentication even if already logged in."}
            }
        }
    },
    {
        "name": "drpr_upload",
        "description": "Upload a file to drpr.host and return the live URL. Requires prior login.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file to upload."},
                "subdomain": {"type": "string", "description": "Optional custom subdomain slug (lowercase, hyphens only)."}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "drpr_status",
        "description": "Check if the user is authenticated with drpr.host.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "drpr_logout",
        "description": "Remove the stored drpr API key.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

HANDLERS = {
    "drpr_login": tool_login,
    "drpr_upload": tool_upload,
    "drpr_status": tool_status,
    "drpr_logout": tool_logout,
}


def handle(request):
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        send(ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "drpr", "version": "1.0.0"}
        }))
    elif method == "tools/list":
        send(ok(req_id, {"tools": TOOLS}))
    elif method == "tools/call":
        name = params.get("name")
        handler = HANDLERS.get(name)
        if not handler:
            send(err(req_id, -32601, f"Unknown tool: {name}"))
            return
        handler(params.get("arguments", {}), req_id)
    elif method == "notifications/initialized":
        pass
    else:
        if req_id is not None:
            send(err(req_id, -32601, f"Method not found: {method}"))


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    main()
