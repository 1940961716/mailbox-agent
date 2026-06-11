from __future__ import annotations

from pathlib import Path
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .agents.langgraph_workflow import process_email_with_langgraph
from .config import FRONTEND_DIR, ensure_runtime_dirs, load_env_file
from .services.llm_service import get_last_llm_error
from .services.imap_service import ImapConfig, fetch_recent_emails_with_meta
from .services.sample_service import load_sample_emails


class ImapSyncRequest(BaseModel):
    host: str
    username: str
    password: str
    port: int = 993
    mailbox: str = "INBOX"
    limit: int = Field(default=50, ge=1, le=200)
    since_date: str | None = None
    until_date: str | None = None
    replace_snapshot: bool = True


class TodoPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: str | None = None
    priority: str | None = None
    status: str | None = None
    evidence: str | None = None


class DraftPatch(BaseModel):
    subject: str | None = None
    body: str | None = None
    status: str | None = None


class ProcessRequest(BaseModel):
    force_todo: bool = False
    force_reply: bool = False


class ProcessAllRequest(BaseModel):
    only_unprocessed: bool = True
    limit: int = Field(default=30, ge=1, le=200)
    force_todo: bool = False
    force_reply: bool = False


app = FastAPI(
    title="智能邮箱助理与自动化待办生成 Agent",
    description="FastAPI + LangGraph implementation of the mailbox assistant MVP.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    load_env_file()
    ensure_runtime_dirs()
    db.init_db()


static_dir = FRONTEND_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(index_path)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "mailbox-agent", "stack": "fastapi+langgraph"}


@app.get("/api/llm/status")
def llm_status() -> dict[str, Any]:
    load_env_file()
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    return {
        "configured": bool(api_key),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "last_error": get_last_llm_error(),
    }


@app.get("/api/emails")
def emails() -> list[dict[str, Any]]:
    return db.list_emails()


@app.get("/api/emails/{email_id}")
def email_detail(email_id: int) -> dict[str, Any]:
    item = db.get_email(email_id)
    if not item:
        raise HTTPException(status_code=404, detail="email not found")
    return item


@app.post("/api/emails/import-samples")
def import_samples() -> dict[str, Any]:
    count = 0
    for item in load_sample_emails():
        db.insert_email(item)
        count += 1
    return {"ok": True, "imported": count, "emails": db.list_emails()}


@app.post("/api/emails/sync")
def sync_emails(payload: ImapSyncRequest) -> dict[str, Any]:
    config = ImapConfig(**payload.model_dump(exclude={"replace_snapshot"}))
    result = fetch_recent_emails_with_meta(config)
    cleared = db.clear_mailbox_snapshot() if payload.replace_snapshot else {}
    imported = 0
    for item in result.emails:
        db.insert_email(item)
        imported += 1
    message = (
        "本时间范围内没有匹配邮件，邮件列表已刷新为空。"
        if imported == 0 and payload.replace_snapshot
        else f"已刷新邮件列表，当前显示 {imported} 封邮件。"
    )
    db.log_agent(
        None,
        "Mailbox Sync",
        f"{payload.username} {payload.since_date or ''}..{payload.until_date or ''}",
        {
            "message": message,
            "imported": imported,
            "server_matched": result.server_matched,
            "criteria": result.criteria,
            "since_date": payload.since_date,
            "until_date": payload.until_date,
            "limit": payload.limit,
            "replace_snapshot": payload.replace_snapshot,
            "cleared": cleared,
        },
        "low",
    )
    return {
        "ok": True,
        "message": message,
        "imported": imported,
        "matched": len(result.emails),
        "server_matched": result.server_matched,
        "criteria": result.criteria,
        "replace_snapshot": payload.replace_snapshot,
        "cleared": cleared,
        "since_date": payload.since_date,
        "until_date": payload.until_date,
        "limit": payload.limit,
    }


@app.post("/api/emails/{email_id}/process")
def process_email(email_id: int, payload: ProcessRequest | None = None) -> dict[str, Any]:
    if not db.get_email(email_id):
        raise HTTPException(status_code=404, detail="email not found")
    payload = payload or ProcessRequest()
    return process_email_with_langgraph(
        email_id,
        force_todo=payload.force_todo,
        force_reply=payload.force_reply,
    )


@app.post("/api/emails/process-all")
def process_all_emails(payload: ProcessAllRequest | None = None) -> dict[str, Any]:
    payload = payload or ProcessAllRequest()
    candidates = db.list_emails()
    if payload.only_unprocessed:
        candidates = [
            item
            for item in candidates
            if item.get("processed_status") in {"new", "unprocessed", None, ""}
        ]
    candidates = candidates[: payload.limit]
    results: list[dict[str, Any]] = []
    for item in candidates:
        email_id = int(item["id"])
        try:
            result = process_email_with_langgraph(
                email_id,
                force_todo=payload.force_todo,
                force_reply=payload.force_reply,
            )
            results.append(
                {
                    "email_id": email_id,
                    "subject": item.get("subject", ""),
                    "ok": True,
                    "category": result.get("triage", {}).get("category"),
                    "risk_level": result.get("critic", {}).get("risk_level"),
                    "todo_count": len(result.get("email", {}).get("todos", [])),
                    "draft_count": len(result.get("email", {}).get("drafts", [])),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "email_id": email_id,
                    "subject": item.get("subject", ""),
                    "ok": False,
                    "error": str(exc),
                }
            )
    return {
        "ok": True,
        "requested": len(candidates),
        "processed": sum(1 for item in results if item.get("ok")),
        "failed": sum(1 for item in results if not item.get("ok")),
        "results": results,
    }


@app.get("/api/todos")
def todos() -> list[dict[str, Any]]:
    return db.list_todos()


@app.patch("/api/todos/{todo_id}")
def patch_todo(todo_id: int, payload: TodoPatch) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    item = db.update_todo(todo_id, patch)
    if not item:
        raise HTTPException(status_code=404, detail="todo not found")
    return item


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int) -> dict[str, Any]:
    if not db.delete_todo(todo_id):
        raise HTTPException(status_code=404, detail="todo not found")
    return {"ok": True, "deleted": todo_id}


@app.get("/api/drafts")
def drafts() -> list[dict[str, Any]]:
    return db.list_drafts()


@app.patch("/api/drafts/{draft_id}")
def patch_draft(draft_id: int, payload: DraftPatch) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    item = db.update_draft(draft_id, patch)
    if not item:
        raise HTTPException(status_code=404, detail="draft not found")
    return item


@app.get("/api/attachments")
def attachments() -> list[dict[str, Any]]:
    return db.list_attachments()


@app.get("/api/agent-logs")
def logs() -> list[dict[str, Any]]:
    return db.list_logs()


@app.get("/{path:path}", include_in_schema=False)
def static_fallback(path: str) -> FileResponse:
    target = (FRONTEND_DIR / path).resolve()
    frontend_root = FRONTEND_DIR.resolve()
    if not str(target).startswith(str(frontend_root)) or not target.exists() or target.is_dir():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(target)
