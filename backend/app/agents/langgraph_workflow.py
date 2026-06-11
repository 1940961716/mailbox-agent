from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .. import db
from ..services.attachment_service import analyze_table
from .action_agent import act_on_email
from .critic_agent import critique
from .triage_agent import triage_email


class MailAgentState(TypedDict, total=False):
    email_id: int
    email: dict[str, Any]
    triage: dict[str, Any]
    attachment_results: list[dict[str, Any]]
    action: dict[str, Any]
    critic: dict[str, Any]
    saved_email: dict[str, Any]
    force_todo: bool
    force_reply: bool


def load_email_node(state: MailAgentState) -> MailAgentState:
    email = db.get_email(int(state["email_id"]))
    if not email:
        raise ValueError(f"email not found: {state['email_id']}")
    return {"email": email}


def triage_node(state: MailAgentState) -> MailAgentState:
    email = state["email"]
    triage = triage_email(email)
    if state.get("force_todo"):
        triage["needs_todo"] = True
        triage["force_todo"] = True
    if state.get("force_reply"):
        triage["needs_reply"] = True
        triage["force_reply"] = True
    db.log_agent(state["email_id"], "Triage Agent", email.get("subject", ""), triage, "low")
    return {"triage": triage}


def attachment_node(state: MailAgentState) -> MailAgentState:
    email = state["email"]
    triage = state["triage"]
    results: list[dict[str, Any]] = []
    if triage.get("needs_attachment_analysis"):
        for attachment in email.get("attachments", []):
            result = analyze_table(attachment.get("path", ""))
            results.append(result)
            db.update_attachment_analysis(attachment["id"], result.get("summary") or result.get("error", ""))
    return {"attachment_results": results}


def action_node(state: MailAgentState) -> MailAgentState:
    action = act_on_email(state["email"], state["triage"], state.get("attachment_results", []))
    db.log_agent(state["email_id"], "Action Agent", state["triage"].get("summary", ""), action, "low")
    return {"action": action}


def critic_node(state: MailAgentState) -> MailAgentState:
    critic = critique(state["email"], state["action"])
    db.log_agent(
        state["email_id"],
        "Critic Agent",
        str(state["action"])[:500],
        critic,
        critic.get("risk_level", "medium"),
    )
    return {"critic": critic}


def save_node(state: MailAgentState) -> MailAgentState:
    email_id = int(state["email_id"])
    action = state["action"]
    critic = state["critic"]
    triage = state["triage"]
    notes = "; ".join(critic.get("issues", []) + critic.get("suggestions", []))
    skipped_todos: list[dict[str, Any]] = []
    for todo in action.get("todos", []):
        existing = db.find_persistent_todo(email_id, todo)
        if existing:
            skipped_todos.append(
                {
                    "todo_id": existing["id"],
                    "title": existing["title"],
                    "status": existing["status"],
                    "reason": "persistent_user_decision_preserved",
                }
            )
            continue
        db.create_todo(email_id, todo, critic_notes=notes)
    if action.get("draft"):
        db.create_draft(email_id, action["draft"], critic_notes=notes)
    if skipped_todos:
        db.log_agent(
            email_id,
            "Persistence Guard",
            "Preserved confirmed/done/rejected Todo items during reprocessing.",
            {"skipped_todos": skipped_todos},
            "low",
        )
    db.update_email_status(email_id, triage["category"], triage["priority"], triage.get("summary", ""))
    return {"saved_email": db.get_email(email_id) or {}}


def build_mail_agent_graph():
    graph = StateGraph(MailAgentState)
    graph.add_node("load_email", load_email_node)
    graph.add_node("triage", triage_node)
    graph.add_node("attachments", attachment_node)
    graph.add_node("action", action_node)
    graph.add_node("critic", critic_node)
    graph.add_node("save", save_node)

    graph.add_edge(START, "load_email")
    graph.add_edge("load_email", "triage")
    graph.add_edge("triage", "attachments")
    graph.add_edge("attachments", "action")
    graph.add_edge("action", "critic")
    graph.add_edge("critic", "save")
    graph.add_edge("save", END)
    return graph.compile()


MAIL_AGENT_GRAPH = build_mail_agent_graph()


def process_email_with_langgraph(email_id: int, force_todo: bool = False, force_reply: bool = False) -> dict[str, Any]:
    cleaned = db.clear_generated_email_outputs(email_id)
    db.log_agent(
        email_id,
        "Persistence Guard",
        "Cleaned only unconfirmed generated outputs before reprocessing.",
        {
            "deleted_pending_todos": cleaned["pending_todos"],
            "deleted_drafts": cleaned["drafts"],
            "preserved_statuses": ["confirmed", "done", "rejected"],
        },
        "low",
    )
    result = MAIL_AGENT_GRAPH.invoke(
        {"email_id": email_id, "force_todo": force_todo, "force_reply": force_reply}
    )
    return {
        "email_id": email_id,
        "triage": result.get("triage", {}),
        "attachment_results": result.get("attachment_results", []),
        "action": result.get("action", {}),
        "critic": result.get("critic", {}),
        "email": result.get("saved_email") or db.get_email(email_id),
        "workflow": "langgraph",
        "force_todo": force_todo,
        "force_reply": force_reply,
    }
