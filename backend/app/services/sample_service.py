from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import SAMPLES_DIR
from .email_parser import parse_eml_bytes


def load_sample_emails() -> list[dict[str, Any]]:
    emails: list[dict[str, Any]] = []
    json_path = SAMPLES_DIR / "sample_emails.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        raw_items = data if isinstance(data, list) else data.get("emails", [])
        for item in raw_items:
            normalized = dict(item)
            attachments = []
            for att in normalized.get("attachments", []):
                item_att = dict(att)
                path = Path(str(item_att.get("path", "")))
                if path and not path.is_absolute():
                    item_att["path"] = str((SAMPLES_DIR / path).resolve())
                attachments.append(item_att)
            normalized["attachments"] = attachments
            emails.append(normalized)
    for eml_path in sorted(SAMPLES_DIR.glob("*.eml")):
        emails.append(parse_eml_bytes(eml_path.read_bytes(), source="sample_eml"))
    return emails
