from __future__ import annotations

import email
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from ..config import ATTACHMENTS_DIR


def decode_mime(value: str | None) -> str:
    if not value:
        return ""
    pieces: list[str] = []
    for part, enc in decode_header(value):
        if isinstance(part, bytes):
            pieces.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            pieces.append(part)
    return "".join(pieces)


def message_body(msg: Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(strip_html(text))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html_parts.append(strip_html(text))
            else:
                plain_parts.append(text)
    return "\n".join(plain_parts or html_parts).strip()


def strip_html(text: str) -> str:
    import re

    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<.*?>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def save_attachments(msg: Message, message_id: str) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    safe_id = "".join(ch if ch.isalnum() else "_" for ch in message_id)[:80] or "mail"
    target_dir = ATTACHMENTS_DIR / safe_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for part in msg.walk():
        filename = decode_mime(part.get_filename())
        disposition = (part.get("Content-Disposition") or "").lower()
        if not filename and "attachment" not in disposition:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        filename = filename or "attachment.bin"
        filename = Path(filename).name
        path = target_dir / filename
        path.write_bytes(payload)
        saved.append(
            {
                "filename": filename,
                "path": str(path),
                "file_type": path.suffix.lower().lstrip("."),
            }
        )
    return saved


def normalize_email_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return parsed.replace(tzinfo=None, microsecond=0).isoformat(sep=" ")
    except Exception:
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.replace(tzinfo=None, microsecond=0).isoformat(sep=" ")
        except Exception:
            return value


def parse_eml_bytes(raw: bytes, source: str = "imap") -> dict[str, Any]:
    msg = email.message_from_bytes(raw)
    message_id = (msg.get("Message-ID") or "").strip("<>") or str(abs(hash(raw)))
    raw_date = msg.get("Date", "")
    return {
        "message_id": message_id,
        "subject": decode_mime(msg.get("Subject")),
        "sender": decode_mime(msg.get("From")),
        "received_at": normalize_email_date(raw_date),
        "raw_received_at": raw_date,
        "body": message_body(msg),
        "summary": "",
        "source": source,
        "attachments": save_attachments(msg, message_id),
    }
