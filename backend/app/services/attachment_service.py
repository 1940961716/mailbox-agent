from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def analyze_table(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {"ok": False, "error": f"file not found: {path}"}
    suffix = file_path.suffix.lower()
    try:
        if suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(file_path)
        elif suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            return {"ok": False, "error": f"unsupported file type: {suffix}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    columns = [str(c) for c in df.columns.tolist()]
    preview = df.head(5).fillna("").to_dict(orient="records")
    task_rows = extract_task_rows(df)
    summary = {
        "ok": True,
        "filename": file_path.name,
        "rows": int(len(df)),
        "columns": columns,
        "preview": preview,
        "task_candidates": task_rows,
        "summary": f"附件 {file_path.name} 共 {len(df)} 行，字段包括：{', '.join(columns)}。",
    }
    return summary


def extract_task_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    lower_map = {str(c).lower(): c for c in df.columns}
    title_key = find_col(lower_map, ["task", "任务", "事项", "title", "工作"])
    owner_key = find_col(lower_map, ["owner", "负责人", "assignee", "责任人"])
    deadline_key = find_col(lower_map, ["deadline", "截止", "due", "日期", "时间"])
    priority_key = find_col(lower_map, ["priority", "优先级", "紧急"])
    if not title_key:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in df.head(20).iterrows():
        title = str(row.get(title_key, "")).strip()
        if not title or title.lower() == "nan":
            continue
        rows.append(
            {
                "title": title,
                "owner": clean(row.get(owner_key, "")) if owner_key else "",
                "deadline": clean(row.get(deadline_key, "")) if deadline_key else "",
                "priority": normalize_priority(clean(row.get(priority_key, ""))) if priority_key else "medium",
                "evidence": f"来自附件表格行：{title}",
                "confidence": 0.78 if deadline_key else 0.62,
            }
        )
    return rows


def find_col(mapping: dict[str, Any], candidates: list[str]) -> Any:
    for cand in candidates:
        for lowered, original in mapping.items():
            if cand.lower() in lowered:
                return original
    return None


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def normalize_priority(value: str) -> str:
    text = value.lower()
    if any(k in text for k in ["high", "高", "紧急", "urgent"]):
        return "high"
    if any(k in text for k in ["low", "低"]):
        return "low"
    return "medium"

