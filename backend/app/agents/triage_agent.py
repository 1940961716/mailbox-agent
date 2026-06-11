from __future__ import annotations

from typing import Any

from ..services.llm_service import call_openai_compatible, get_last_llm_error


def triage_email(email: dict[str, Any]) -> dict[str, Any]:
    subject = email.get("subject", "")
    body = email.get("body", "")
    attachments = email.get("attachments", [])
    user_text = (
        f"邮件标题：{subject}\n"
        f"发件人：{email.get('sender', '')}\n"
        f"收件时间：{email.get('received_at', '')}\n"
        f"附件：{attachments}\n"
        f"正文：{body[:3000]}\n"
    )
    llm = call_openai_compatible(
        (
            "你是邮件分类智能体。只输出 JSON，不要 Markdown。字段："
            "category(task/meeting/notification/needs_reply/ignore/security), "
            "priority(high/medium/low), needs_todo, needs_reply, "
            "needs_attachment_analysis, summary, evidence, confidence。"
        ),
        user_text,
    )
    if llm:
        result = normalize(llm)
        result["llm_status"] = "ok"
        if llm.get("_llm_warning"):
            result["llm_warning"] = llm["_llm_warning"]
        return result
    result = rule_triage(subject, body, attachments)
    result["llm_status"] = "fallback"
    result["llm_error"] = get_last_llm_error()
    return result


def rule_triage(subject: str, body: str, attachments: list[dict[str, Any]]) -> dict[str, Any]:
    text = f"{subject}\n{body}".lower()
    original = f"{subject}\n{body}"
    attachment_analysis = any(str(a.get("filename", "")).lower().endswith((".xlsx", ".xls", ".csv")) for a in attachments)
    needs_reply = any(k in text for k in ["please reply", "confirm", "feedback", "re:", "回复", "确认", "请反馈", "能否"])
    needs_todo = any(k in original for k in ["请", "需要", "提交", "完成", "截止", "下周", "明天", "今天", "本周", "任务", "安排"])
    meeting = any(k in original.lower() for k in ["会议", "开会", "参会", "日程", "meeting"])
    ignore = any(k in original.lower() for k in ["广告", "订阅", "促销", "newsletter", "notification only"])
    security = any(k in original.lower() for k in ["oauth", "security", "安全", "登录", "验证码"])
    if ignore and not needs_todo:
        category = "ignore"
    elif security:
        category = "security"
    elif meeting:
        category = "meeting"
    elif needs_todo:
        category = "task"
    elif needs_reply:
        category = "needs_reply"
    else:
        category = "notification"
    priority = "high" if any(k in original.lower() for k in ["紧急", "尽快", "今天", "明天", "截止", "urgent"]) else "medium"
    summary = body.strip().replace("\n", " ")[:120] or subject
    return {
        "category": category,
        "priority": priority,
        "needs_todo": needs_todo or attachment_analysis,
        "needs_reply": needs_reply,
        "needs_attachment_analysis": attachment_analysis,
        "summary": summary,
        "evidence": "基于关键词、附件类型和邮件主题的规则分类。",
        "confidence": 0.72,
    }


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": data.get("category", "notification"),
        "priority": data.get("priority", "medium"),
        "needs_todo": bool(data.get("needs_todo", False)),
        "needs_reply": bool(data.get("needs_reply", False)),
        "needs_attachment_analysis": bool(data.get("needs_attachment_analysis", False)),
        "summary": data.get("summary", ""),
        "evidence": data.get("evidence", ""),
        "confidence": float(data.get("confidence", 0.8) or 0.8),
    }
