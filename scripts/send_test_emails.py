from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTACHMENT = ROOT / "samples" / "outgoing_project_tasks.csv"


@dataclass
class MailCase:
    key: str
    subject: str
    body: str
    attachment: Path | None = None
    tags: list[str] = field(default_factory=list)


CASES = [
    MailCase(
        key="task",
        subject="【任务】请在本周五前提交智能邮箱 Agent 演示视频",
        body=(
            "你好，\n\n"
            "请在本周五下班前提交智能邮箱 Agent 的项目演示视频。"
            "视频需要展示真实邮箱同步、Agent 分类、Todo 生成、回复草稿生成、附件分析和 Critic 审查。\n\n"
            "完成后请回复邮件确认，并说明是否还有阻塞问题。\n\n"
            "谢谢。"
        ),
        tags=["todo", "reply", "deadline"],
    ),
    MailCase(
        key="reply",
        subject="请确认 MVP 是否已经支持附件分析",
        body=(
            "你好，\n\n"
            "请确认当前 MVP 是否支持读取 Excel 或 CSV 附件，并把表格中的任务转成 Todo。"
            "如果可以，请回复一个简短说明，包含支持的附件格式和当前限制。\n\n"
            "谢谢。"
        ),
        tags=["reply"],
    ),
    MailCase(
        key="meeting",
        subject="周四下午项目评审会议通知",
        body=(
            "各位同学好，\n\n"
            "本周四下午 3 点进行项目评审会议，请准备 5 分钟演示。"
            "重点说明敏捷过程文件、Agent 工作流、真实邮箱接入和当前可运行功能。\n\n"
            "如无法参加，请提前回复确认。"
        ),
        tags=["meeting", "todo"],
    ),
    MailCase(
        key="attachment",
        subject="本周项目任务表，请根据附件推进",
        body=(
            "团队好，\n\n"
            "附件中是本周项目任务表，请根据 owner 和 deadline 推进。"
            "高优先级任务请优先完成，明天下班前同步一次进展。\n\n"
            "请 Agent 自动分析附件并生成 Todo。"
        ),
        attachment=DEFAULT_ATTACHMENT,
        tags=["attachment", "todo"],
    ),
    MailCase(
        key="ambiguous_time",
        subject="请明天下班前整理最终答辩材料",
        body=(
            "你好，\n\n"
            "请明天下班前整理最终答辩材料，包括运行说明、测试截图、项目总结和敏捷过程文件。"
            "如果有任何不确定的时间或内容，请在 Todo 中标记需要人工确认。\n\n"
            "谢谢。"
        ),
        tags=["todo", "ambiguous_time"],
    ),
    MailCase(
        key="security",
        subject="【安全提醒】测试邮箱新增第三方授权，请确认是否本人操作",
        body=(
            "你好，\n\n"
            "系统检测到你的测试邮箱新增了一个第三方授权。"
            "请确认是否为本人操作。如果不是，请尽快撤销授权并修改授权码。\n\n"
            "本邮件用于测试安全类邮件是否能生成跟进 Todo。"
        ),
        tags=["security", "todo"],
    ),
    MailCase(
        key="notification",
        subject="课程资料更新通知，无需回复",
        body=(
            "各位同学好，\n\n"
            "课程资料已更新到平台，请有需要时自行查看。本邮件无需回复，也不要求立即处理。\n\n"
            "谢谢。"
        ),
        tags=["notification"],
    ),
]


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def selected_cases(selector: str) -> list[MailCase]:
    if selector == "all":
        return CASES
    requested = {item.strip() for item in selector.split(",") if item.strip()}
    cases = [case for case in CASES if case.key in requested]
    missing = requested - {case.key for case in cases}
    if missing:
        raise SystemExit(f"未知测试邮件: {', '.join(sorted(missing))}")
    return cases


def build_message(case: MailCase, sender: str, recipient: str, prefix: str = "") -> EmailMessage:
    msg = EmailMessage()
    subject_prefix = f"{prefix.strip()} " if prefix.strip() else ""
    msg["Subject"] = f"{subject_prefix}{case.subject}"
    msg["From"] = sender
    msg["To"] = recipient
    msg["X-Mailbox-Agent-Test"] = case.key
    msg.set_content(case.body, subtype="plain", charset="utf-8")

    if case.attachment:
        if not case.attachment.exists():
            raise FileNotFoundError(f"附件不存在: {case.attachment}")
        data = case.attachment.read_bytes()
        maintype, subtype = content_type(case.attachment)
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=case.attachment.name,
        )
    return msg


def content_type(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "text", "csv"
    if suffix in {".xlsx", ".xls"}:
        return "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application", "octet-stream"


def send_messages(cases: Iterable[MailCase], dry_run: bool, prefix: str) -> None:
    host = env("SMTP_HOST", "smtp.163.com")
    port = int(env("SMTP_PORT", "465"))
    sender = env("SMTP_USER")
    password = env("SMTP_AUTH_CODE") or env("SMTP_PASSWORD")
    recipient = env("TEST_TO_EMAIL")
    use_ssl = env("SMTP_SSL", "true").lower() not in {"0", "false", "no"}

    if dry_run:
        sender = sender or "your_sender@163.com"
        recipient = recipient or "your_receiver@qq.com"

    if not sender or not recipient:
        raise SystemExit("缺少 SMTP_USER 或 TEST_TO_EMAIL，请先配置 .env。")
    if not dry_run and not password:
        raise SystemExit("缺少 SMTP_AUTH_CODE，请配置 163 邮箱授权码。")

    messages = [build_message(case, sender, recipient, prefix) for case in cases]
    print(f"sender={sender}")
    print(f"recipient={recipient}")
    print(f"smtp={host}:{port} ssl={use_ssl}")
    print(f"count={len(messages)} dry_run={dry_run}")

    for case, msg in zip(cases, messages):
        attachment_names = [part.get_filename() for part in msg.iter_attachments()]
        print(f"- {case.key}: {msg['Subject']} attachments={attachment_names or 'none'}")

    if dry_run:
        print("dry-run 完成：未发送邮件。加 --send 才会真实发送。")
        return

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(sender, password)
            for msg in messages:
                server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(sender, password)
            for msg in messages:
                server.send_message(msg)
    print("发送完成。请到测试邮箱收件箱查看。")


def main() -> None:
    parser = argparse.ArgumentParser(description="发送智能邮箱 Agent 测试邮件。")
    parser.add_argument(
        "--case",
        default="all",
        help="测试邮件 key，多个用逗号分隔；默认 all。可选："
        + ", ".join(case.key for case in CASES),
    )
    parser.add_argument("--send", action="store_true", help="真实发送邮件。默认 dry-run。")
    parser.add_argument("--list", action="store_true", help="列出测试邮件，不发送。")
    parser.add_argument("--prefix", default="[Agent测试]", help="邮件主题前缀。")
    args = parser.parse_args()

    load_env()
    cases = selected_cases(args.case)
    if args.list:
        for case in cases:
            print(f"{case.key}: {case.subject} tags={','.join(case.tags)}")
        return
    send_messages(cases, dry_run=not args.send, prefix=args.prefix)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
