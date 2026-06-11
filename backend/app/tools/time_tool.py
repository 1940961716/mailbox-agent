from __future__ import annotations

from datetime import datetime, timedelta
import re


def current_time_context() -> dict[str, str]:
    now = datetime.now()
    return {
        "now": now.replace(microsecond=0).isoformat(sep=" "),
        "date": now.date().isoformat(),
        "timezone": "Asia/Shanghai",
        "weekday": str(now.weekday() + 1),
    }


def parse_cn_deadline(text: str) -> tuple[str, float, str]:
    now = datetime.now()
    normalized = text.replace(" ", "")
    if "明天" in normalized:
        target = now + timedelta(days=1)
        hour = 18 if any(k in normalized for k in ["下班", "下午", "前"]) else 23
        return target.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat(sep=" "), 0.82, "明天"
    if "后天" in normalized:
        target = now + timedelta(days=2)
        return target.replace(hour=18, minute=0, second=0, microsecond=0).isoformat(sep=" "), 0.78, "后天"
    if "本周五" in normalized or "周五" in normalized:
        days = (4 - now.weekday()) % 7
        target = now + timedelta(days=days)
        return target.replace(hour=18, minute=0, second=0, microsecond=0).isoformat(sep=" "), 0.76, "周五"
    if "下周三" in normalized:
        days = (2 - now.weekday()) % 7 + 7
        target = now + timedelta(days=days)
        return target.replace(hour=18, minute=0, second=0, microsecond=0).isoformat(sep=" "), 0.74, "下周三"
    if "月底" in normalized or "本月底" in normalized:
        if now.month == 12:
            first_next = now.replace(year=now.year + 1, month=1, day=1)
        else:
            first_next = now.replace(month=now.month + 1, day=1)
        target = first_next - timedelta(days=1)
        return target.replace(hour=18, minute=0, second=0, microsecond=0).isoformat(sep=" "), 0.70, "月底"
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if match:
        y, m, d = map(int, match.groups())
        return datetime(y, m, d, 18, 0, 0).isoformat(sep=" "), 0.9, match.group(0)
    return "", 0.0, ""

