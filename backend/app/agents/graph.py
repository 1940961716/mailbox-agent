from __future__ import annotations

from typing import Any

from .. import db
from ..services.attachment_service import analyze_table
from .action_agent import act_on_email
from .critic_agent import critique
from .triage_agent import triage_email


def process_email(email_id: int) -> dict[str, Any]:
    email = db.get_email(email_id)
    if not email:
        raise ValueError(f"email not found: {email_id}")
    db.clear_email_outputs(email_id)
    email = db.get_email(email_id)

    triage = triage_email(email)
    db.log_agent(email_id, "Triage Agent", email.get("subject", ""), triage, "low")

    attachment_results: list[dict[str, Any]] = []
    if triage.get("needs_attachment_analysis"):
        for attachment in email.get("attachments", []):
            result = analyze_table(attachment.get("path", ""))
            attachment_results.append(result)
            db.update_attachment_analysis(attachment["id"], result.get("summary") or result.get("error", ""))

    action = act_on_email(email, triage, attachment_results)
    db.log_agent(email_id, "Action Agent", triage.get("summary", ""), action, "low")

    critic = critique(email, action)
    db.log_agent(email_id, "Critic Agent", str(action)[:500], critic, critic.get("risk_level", "medium"))

    notes = "; ".join(critic.get("issues", []) + critic.get("suggestions", []))
    for todo in action.get("todos", []):
        db.create_todo(email_id, todo, critic_notes=notes)
    if action.get("draft"):
        db.create_draft(email_id, action["draft"], critic_notes=notes)
    db.update_email_status(email_id, triage["category"], triage["priority"], triage.get("summary", ""))

    return {
        "email_id": email_id,
        "triage": triage,
        "attachment_results": attachment_results,
        "action": action,
        "critic": critic,
        "email": db.get_email(email_id),
    }
