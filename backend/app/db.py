from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, ensure_runtime_dirs


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            create table if not exists emails (
                id integer primary key autoincrement,
                message_id text unique,
                subject text not null,
                sender text,
                received_at text,
                body text,
                summary text,
                category text default 'unprocessed',
                priority text default 'medium',
                processed_status text default 'new',
                source text default 'sample',
                raw_json text,
                created_at text not null
            );

            create table if not exists attachments (
                id integer primary key autoincrement,
                email_id integer not null,
                filename text not null,
                path text not null,
                file_type text,
                analysis_summary text,
                created_at text not null,
                foreign key(email_id) references emails(id)
            );

            create table if not exists todos (
                id integer primary key autoincrement,
                email_id integer not null,
                title text not null,
                description text,
                deadline text,
                priority text default 'medium',
                status text default 'pending',
                evidence text,
                confidence real default 0.0,
                critic_notes text,
                created_at text not null,
                updated_at text not null,
                foreign key(email_id) references emails(id)
            );

            create table if not exists drafts (
                id integer primary key autoincrement,
                email_id integer not null,
                subject text not null,
                body text not null,
                status text default 'draft',
                critic_notes text,
                created_at text not null,
                updated_at text not null,
                foreign key(email_id) references emails(id)
            );

            create table if not exists agent_logs (
                id integer primary key autoincrement,
                email_id integer,
                agent_name text not null,
                input_summary text,
                output_json text,
                risk_level text default 'low',
                created_at text not null
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) or {} for row in rows]


def insert_email(email: dict[str, Any]) -> int:
    payload = dict(email)
    message_id = payload.get("message_id") or f"sample-{abs(hash(json.dumps(payload, ensure_ascii=False, sort_keys=True)))}"
    attachments = payload.pop("attachments", [])
    with connect() as conn:
        existing = conn.execute("select id from emails where message_id = ?", (message_id,)).fetchone()
        if existing:
            email_id = int(existing["id"])
        else:
            cur = conn.execute(
                """
                insert into emails (
                    message_id, subject, sender, received_at, body, summary,
                    category, priority, processed_status, source, raw_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    payload.get("subject", "(no subject)"),
                    payload.get("sender", ""),
                    payload.get("received_at", ""),
                    payload.get("body", ""),
                    payload.get("summary", ""),
                    payload.get("category", "unprocessed"),
                    payload.get("priority", "medium"),
                    payload.get("processed_status", "new"),
                    payload.get("source", "sample"),
                    json.dumps(email, ensure_ascii=False),
                    now_iso(),
                ),
            )
            email_id = int(cur.lastrowid)

        for att in attachments:
            path = str(att.get("path", ""))
            filename = att.get("filename") or Path(path).name
            if not filename:
                continue
            exists = conn.execute(
                "select id from attachments where email_id = ? and filename = ?",
                (email_id, filename),
            ).fetchone()
            if not exists:
                conn.execute(
                    """
                    insert into attachments (email_id, filename, path, file_type, analysis_summary, created_at)
                    values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email_id,
                        filename,
                        path,
                        att.get("file_type", Path(filename).suffix.lower().lstrip(".")),
                        att.get("analysis_summary", ""),
                        now_iso(),
                    ),
                )
        return email_id


def list_emails() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            select e.*,
                   (select count(*) from attachments a where a.email_id = e.id) as attachment_count,
                   (select count(*) from todos t where t.email_id = e.id) as todo_count,
                   (select count(*) from drafts d where d.email_id = e.id) as draft_count
            from emails e
            order by datetime(coalesce(nullif(received_at, ''), created_at)) desc, id desc
            """
        ).fetchall()
        return rows_to_dicts(rows)


def clear_mailbox_snapshot() -> dict[str, int]:
    with connect() as conn:
        counts = {
            "emails": conn.execute("select count(*) from emails").fetchone()[0],
            "todos": conn.execute("select count(*) from todos").fetchone()[0],
            "drafts": conn.execute("select count(*) from drafts").fetchone()[0],
            "attachments": conn.execute("select count(*) from attachments").fetchone()[0],
            "agent_logs": conn.execute("select count(*) from agent_logs").fetchone()[0],
        }
        conn.execute("delete from todos")
        conn.execute("delete from drafts")
        conn.execute("delete from agent_logs")
        conn.execute("delete from attachments")
        conn.execute("delete from emails")
        return counts


def get_email(email_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        email = row_to_dict(conn.execute("select * from emails where id = ?", (email_id,)).fetchone())
        if not email:
            return None
        email["attachments"] = rows_to_dicts(
            conn.execute("select * from attachments where email_id = ?", (email_id,)).fetchall()
        )
        email["todos"] = rows_to_dicts(
            conn.execute("select * from todos where email_id = ? order by id desc", (email_id,)).fetchall()
        )
        email["drafts"] = rows_to_dicts(
            conn.execute("select * from drafts where email_id = ? order by id desc", (email_id,)).fetchall()
        )
        email["logs"] = rows_to_dicts(
            conn.execute("select * from agent_logs where email_id = ? order by id desc", (email_id,)).fetchall()
        )
        return email


def update_email_status(email_id: int, category: str, priority: str, summary: str, status: str = "processed") -> None:
    with connect() as conn:
        conn.execute(
            """
            update emails
            set category = ?, priority = ?, summary = ?, processed_status = ?
            where id = ?
            """,
            (category, priority, summary, status, email_id),
        )


def create_todo(email_id: int, todo: dict[str, Any], critic_notes: str = "") -> int:
    ts = now_iso()
    with connect() as conn:
        cur = conn.execute(
            """
            insert into todos (
                email_id, title, description, deadline, priority, status,
                evidence, confidence, critic_notes, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email_id,
                todo.get("title", "未命名任务"),
                todo.get("description", ""),
                todo.get("deadline", ""),
                todo.get("priority", "medium"),
                todo.get("status", "pending"),
                todo.get("evidence", ""),
                float(todo.get("confidence", 0.0) or 0.0),
                critic_notes,
                ts,
                ts,
            ),
        )
        return int(cur.lastrowid)


def find_persistent_todo(email_id: int, todo: dict[str, Any]) -> dict[str, Any] | None:
    title = (todo.get("title") or "").strip()
    evidence = (todo.get("evidence") or "").strip()
    if not title:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            select * from todos
            where email_id = ?
              and title = ?
              and status in ('confirmed', 'done', 'rejected')
              and (coalesce(evidence, '') = ? or ? = '')
            order by id desc
            limit 1
            """,
            (email_id, title, evidence, evidence),
        ).fetchone()
        return row_to_dict(row)


def create_draft(email_id: int, draft: dict[str, Any], critic_notes: str = "") -> int:
    ts = now_iso()
    with connect() as conn:
        cur = conn.execute(
            """
            insert into drafts (email_id, subject, body, status, critic_notes, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email_id,
                draft.get("subject", "Re:"),
                draft.get("body", ""),
                draft.get("status", "draft"),
                critic_notes,
                ts,
                ts,
            ),
        )
        return int(cur.lastrowid)


def list_todos() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                select t.*, e.subject as email_subject, e.sender as email_sender
                from todos t join emails e on e.id = t.email_id
                order by case t.status when 'pending' then 0 when 'confirmed' then 1 else 2 end,
                         coalesce(t.deadline, '') asc,
                         t.id desc
                """
            ).fetchall()
        )


def update_todo(todo_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"title", "description", "deadline", "priority", "status", "evidence"}
    fields = [(k, v) for k, v in patch.items() if k in allowed]
    if not fields:
        with connect() as conn:
            return row_to_dict(conn.execute("select * from todos where id = ?", (todo_id,)).fetchone())
    assignments = ", ".join(f"{k} = ?" for k, _ in fields) + ", updated_at = ?"
    values = [v for _, v in fields] + [now_iso(), todo_id]
    with connect() as conn:
        conn.execute(f"update todos set {assignments} where id = ?", values)
        return row_to_dict(conn.execute("select * from todos where id = ?", (todo_id,)).fetchone())


def delete_todo(todo_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("delete from todos where id = ?", (todo_id,))
        return cur.rowcount > 0


def list_drafts() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                select d.*, e.subject as email_subject, e.sender as email_sender
                from drafts d join emails e on e.id = d.email_id
                order by d.id desc
                """
            ).fetchall()
        )


def update_draft(draft_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"subject", "body", "status"}
    fields = [(k, v) for k, v in patch.items() if k in allowed]
    if not fields:
        with connect() as conn:
            return row_to_dict(conn.execute("select * from drafts where id = ?", (draft_id,)).fetchone())
    assignments = ", ".join(f"{k} = ?" for k, _ in fields) + ", updated_at = ?"
    values = [v for _, v in fields] + [now_iso(), draft_id]
    with connect() as conn:
        conn.execute(f"update drafts set {assignments} where id = ?", values)
        return row_to_dict(conn.execute("select * from drafts where id = ?", (draft_id,)).fetchone())


def list_attachments() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                select a.*, e.subject as email_subject
                from attachments a join emails e on e.id = a.email_id
                order by a.id desc
                """
            ).fetchall()
        )


def get_attachment(attachment_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(conn.execute("select * from attachments where id = ?", (attachment_id,)).fetchone())


def update_attachment_analysis(attachment_id: int, summary: str) -> None:
    with connect() as conn:
        conn.execute("update attachments set analysis_summary = ? where id = ?", (summary, attachment_id))


def log_agent(email_id: int | None, agent_name: str, input_summary: str, output: dict[str, Any], risk_level: str = "low") -> None:
    with connect() as conn:
        conn.execute(
            """
            insert into agent_logs (email_id, agent_name, input_summary, output_json, risk_level, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (email_id, agent_name, input_summary, json.dumps(output, ensure_ascii=False), risk_level, now_iso()),
        )


def clear_email_outputs(email_id: int) -> None:
    with connect() as conn:
        conn.execute("delete from todos where email_id = ?", (email_id,))
        conn.execute("delete from drafts where email_id = ?", (email_id,))
        conn.execute("delete from agent_logs where email_id = ?", (email_id,))
        conn.execute("update attachments set analysis_summary = '' where email_id = ?", (email_id,))


def clear_generated_email_outputs(email_id: int) -> dict[str, int]:
    with connect() as conn:
        todo_cur = conn.execute(
            "delete from todos where email_id = ? and status = 'pending'",
            (email_id,),
        )
        draft_cur = conn.execute(
            "delete from drafts where email_id = ? and status = 'draft'",
            (email_id,),
        )
        return {"pending_todos": todo_cur.rowcount, "drafts": draft_cur.rowcount}


def list_logs() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(conn.execute("select * from agent_logs order by id desc").fetchall())
