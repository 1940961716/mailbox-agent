from __future__ import annotations

import json
import mimetypes
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db
from .agents.graph import process_email
from .config import FRONTEND_DIR, ensure_runtime_dirs, load_env_file
from .services.imap_service import ImapConfig, fetch_recent_emails
from .services.sample_service import load_sample_emails


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "MailboxAgent/0.1"

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                self.json_response({"ok": True, "service": "mailbox-agent"})
            elif path == "/api/emails":
                self.json_response(db.list_emails())
            elif path.startswith("/api/emails/"):
                email_id = int(path.rsplit("/", 1)[-1])
                item = db.get_email(email_id)
                self.json_response(item or {"error": "not found"}, 200 if item else 404)
            elif path == "/api/todos":
                self.json_response(db.list_todos())
            elif path == "/api/drafts":
                self.json_response(db.list_drafts())
            elif path == "/api/attachments":
                self.json_response(db.list_attachments())
            elif path == "/api/agent-logs":
                self.json_response(db.list_logs())
            else:
                self.serve_static(path)
        except Exception as exc:
            self.error_response(exc)

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self.read_json()
            if path == "/api/emails/import-samples":
                count = 0
                for item in load_sample_emails():
                    db.insert_email(item)
                    count += 1
                self.json_response({"ok": True, "imported": count, "emails": db.list_emails()})
            elif path == "/api/emails/sync":
                config = ImapConfig(
                    host=body.get("host", ""),
                    username=body.get("username", ""),
                    password=body.get("password", ""),
                    port=int(body.get("port", 993)),
                    mailbox=body.get("mailbox", "INBOX"),
                    limit=int(body.get("limit", 10)),
                )
                imported = 0
                for item in fetch_recent_emails(config):
                    db.insert_email(item)
                    imported += 1
                self.json_response({"ok": True, "imported": imported})
            elif path.startswith("/api/emails/") and path.endswith("/process"):
                email_id = int(path.split("/")[-2])
                self.json_response(process_email(email_id))
            else:
                self.json_response({"error": "not found"}, 404)
        except Exception as exc:
            self.error_response(exc)

    def do_PATCH(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self.read_json()
            if path.startswith("/api/todos/"):
                todo_id = int(path.rsplit("/", 1)[-1])
                self.json_response(db.update_todo(todo_id, body) or {"error": "not found"})
            elif path.startswith("/api/drafts/"):
                draft_id = int(path.rsplit("/", 1)[-1])
                self.json_response(db.update_draft(draft_id, body) or {"error": "not found"})
            else:
                self.json_response({"error": "not found"}, 404)
        except Exception as exc:
            self.error_response(exc)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def json_response(self, data, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.json_response({})

    def error_response(self, exc: Exception) -> None:
        traceback.print_exc()
        self.json_response({"error": str(exc), "type": exc.__class__.__name__}, 500)

    def serve_static(self, path: str) -> None:
        if path == "/":
            target = FRONTEND_DIR / "index.html"
        else:
            target = (FRONTEND_DIR / path.lstrip("/")).resolve()
            if not str(target).startswith(str(FRONTEND_DIR.resolve())):
                self.json_response({"error": "forbidden"}, 403)
                return
        if not target.exists() or target.is_dir():
            self.json_response({"error": "not found"}, 404)
            return
        content = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    load_env_file()
    ensure_runtime_dirs()
    db.init_db()
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Mailbox Agent running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

