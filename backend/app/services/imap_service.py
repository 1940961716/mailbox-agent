from __future__ import annotations

import imaplib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from .email_parser import parse_eml_bytes


@dataclass
class ImapConfig:
    host: str
    username: str
    password: str
    port: int = 993
    mailbox: str = "INBOX"
    limit: int = 10
    since_date: str | None = None
    until_date: str | None = None


@dataclass
class ImapFetchResult:
    emails: list[dict[str, Any]]
    server_matched: int
    criteria: list[str]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _imap_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


def _search_criteria(config: ImapConfig) -> list[str]:
    since = _parse_date(config.since_date)
    until = _parse_date(config.until_date)
    criteria: list[str] = []
    if since:
        criteria.extend(["SINCE", _imap_date(since)])
    if until:
        # IMAP BEFORE is exclusive, so add one day to make the UI end date inclusive.
        criteria.extend(["BEFORE", _imap_date(until + timedelta(days=1))])
    return criteria or ["ALL"]


def _email_in_date_range(item: dict[str, Any], config: ImapConfig) -> bool:
    since = _parse_date(config.since_date)
    until = _parse_date(config.until_date)
    if not since and not until:
        return True
    value = item.get("received_at") or ""
    try:
        received_date = datetime.fromisoformat(value).date()
    except Exception:
        return True
    if since and received_date < since:
        return False
    if until and received_date > until:
        return False
    return True


def fetch_recent_emails_with_meta(config: ImapConfig) -> ImapFetchResult:
    emails: list[dict] = []
    with imaplib.IMAP4_SSL(config.host, config.port) as client:
        client.login(config.username, config.password)
        client.select(config.mailbox)
        criteria = _search_criteria(config)
        typ, data = client.search(None, *criteria)
        if typ != "OK":
            raise RuntimeError("IMAP search failed")
        ids = data[0].split()
        for msg_id in reversed(ids):
            typ, msg_data = client.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data:
                continue
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                item = parse_eml_bytes(raw, source="imap")
                if _email_in_date_range(item, config):
                    emails.append(item)
                if len(emails) >= config.limit:
                    break
        return ImapFetchResult(emails=emails, server_matched=len(ids), criteria=criteria)


def fetch_recent_emails(config: ImapConfig) -> list[dict]:
    return fetch_recent_emails_with_meta(config).emails
