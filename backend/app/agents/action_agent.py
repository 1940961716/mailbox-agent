from __future__ import annotations

from typing import Any

from ..services.llm_service import call_openai_compatible, get_last_llm_error
from ..tools.time_tool import parse_cn_deadline


def act_on_email(email: dict[str, Any], triage: dict[str, Any], attachment_results: list[dict[str, Any]]) -> dict[str, Any]:
    user_text = (
        f"邮件标题：{email.get('subject')}\n"
        f"发件人：{email.get('sender')}\n"
        f"收件时间：{email.get('received_at', '')}\n"
        f"正文：{email.get('body', '')[:3000]}\n"
        f"分类结果：{triage}\n"
        f"附件分析：{attachment_results}\n"
    )
    llm = call_openai_compatible(
        (
            "你是邮件执行智能体。只输出 JSON，不要 Markdown。字段："
            "todos 数组、draft 对象或 null、notes。"
            "Todo 字段必须包含 title, description, deadline, priority, status, "
            "evidence, confidence。草稿字段包含 subject, body, status。"
            "如果邮件不需要任务或回复，可以返回空数组或 null。"
        ),
        user_text,
    )
    if llm:
        normalized = normalize_action(llm, email)
        normalized["llm_status"] = "ok"
        normalized["llm_model"] = llm.get("_llm_model", "")
        normalized["llm_provider"] = llm.get("_llm_provider", "")
        if llm.get("_llm_warning"):
            normalized["llm_warning"] = llm["_llm_warning"]
        return ensure_forced_outputs(normalized, email, triage)
    fallback = rule_action(email, triage, attachment_results)
    fallback["llm_status"] = "fallback"
    fallback["llm_error"] = get_last_llm_error() or "LLM returned no usable JSON; rule fallback was used."
    return fallback


def rule_action(email: dict[str, Any], triage: dict[str, Any], attachment_results: list[dict[str, Any]]) -> dict[str, Any]:
    subject = email.get("subject", "")
    body = email.get("body", "")
    todos: list[dict[str, Any]] = []
    deadline, confidence, expr = parse_cn_deadline(f"{subject}\n{body}")
    if triage.get("needs_todo") or triage.get("force_todo"):
        todos.append(
            {
                "title": infer_title(subject, body),
                "description": body[:260],
                "deadline": deadline,
                "priority": triage.get("priority", "medium"),
                "status": "pending",
                "evidence": expr or body[:120],
                "confidence": max(confidence, 0.66 if deadline else 0.55),
            }
        )
    for result in attachment_results:
        for row in result.get("task_candidates", []) if result.get("ok") else []:
            todos.append(
                {
                    "title": row.get("title", "附件任务"),
                    "description": f"来自附件：{result.get('filename', '')}；负责人：{row.get('owner', '')}",
                    "deadline": row.get("deadline", ""),
                    "priority": row.get("priority", "medium"),
                    "status": "pending",
                    "evidence": row.get("evidence", ""),
                    "confidence": row.get("confidence", 0.7),
                }
            )
    draft = None
    if triage.get("needs_reply") or triage.get("force_reply"):
        draft = {
            "subject": subject if subject.lower().startswith("re:") else f"Re: {subject}",
            "body": build_draft(email, todos),
            "status": "draft",
        }
    return {"todos": todos, "draft": draft, "notes": "规则型 Action Agent 输出。"}


def infer_title(subject: str, body: str) -> str:
    if subject:
        return subject.replace("回复：", "").replace("Re:", "").strip()[:60]
    for line in body.splitlines():
        line = line.strip()
        if line:
            return line[:60]
    return "处理邮件任务"


def build_draft(email: dict[str, Any], todos: list[dict[str, Any]]) -> str:
    todo_line = f"我会跟进“{todos[0]['title']}”。" if todos else "我已收到您的邮件，会尽快跟进相关事项。"
    return (
        "您好，\n\n"
        f"邮件已收到。{todo_line}\n"
        "如有进一步材料或时间要求，我会及时同步。\n\n"
        "谢谢。"
    )


def normalize_action(data: dict[str, Any], email: dict[str, Any]) -> dict[str, Any]:
    todos = data.get("todos") or []
    draft = data.get("draft")
    for todo in todos:
        todo.setdefault("title", infer_title(email.get("subject", ""), email.get("body", "")))
        todo.setdefault("description", "")
        todo.setdefault("deadline", "")
        todo.setdefault("status", "pending")
        todo.setdefault("priority", "medium")
        todo.setdefault("evidence", "")
        todo.setdefault("confidence", 0.75)
    if draft:
        draft.setdefault("subject", f"Re: {email.get('subject', '')}")
        draft.setdefault("body", "")
        draft.setdefault("status", "draft")
    return {"todos": todos, "draft": draft, "notes": data.get("notes", "LLM Action Agent 输出。")}


def ensure_forced_outputs(action: dict[str, Any], email: dict[str, Any], triage: dict[str, Any]) -> dict[str, Any]:
    if triage.get("force_todo") and not action.get("todos"):
        title = infer_title(email.get("subject", ""), email.get("body", ""))
        action["todos"] = [
            {
                "title": f"跟进：{title}",
                "description": email.get("body", "")[:260],
                "deadline": "",
                "priority": triage.get("priority", "medium"),
                "status": "pending",
                "evidence": "用户手动要求从该邮件生成 Todo。",
                "confidence": 0.58,
            }
        ]
    if triage.get("force_reply") and not action.get("draft"):
        action["draft"] = {
            "subject": f"Re: {email.get('subject', '')}",
            "body": build_draft(email, action.get("todos", [])),
            "status": "draft",
        }
    if triage.get("force_todo") or triage.get("force_reply"):
        action["notes"] = f"{action.get('notes', '')} 用户强制生成结果。".strip()
    return action
