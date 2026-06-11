from __future__ import annotations

from typing import Any

from ..services.llm_service import call_openai_compatible, get_last_llm_error


def critique(email: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    llm = call_openai_compatible(
        (
            "你是严谨性审查智能体。检查 Todo 和回复草稿是否有风险。"
            "只输出 JSON，不要 Markdown。字段：risk_level(low/medium/high), "
            "issues 数组, suggestions 数组。重点检查模糊时间、缺少证据、过度承诺、隐私风险。"
        ),
        f"邮件：{email}\n执行结果：{action}",
    )
    if llm:
        result = normalize(llm)
        result["llm_status"] = "ok"
        if llm.get("_llm_warning"):
            result["llm_warning"] = llm["_llm_warning"]
        return result
    result = rule_critique(action)
    result["llm_status"] = "fallback"
    result["llm_error"] = get_last_llm_error()
    return result


def rule_critique(action: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    suggestions: list[str] = []
    for todo in action.get("todos", []):
        title = todo.get("title", "未命名任务")
        if not todo.get("deadline"):
            issues.append(f"任务“{title}”缺少明确截止时间。")
            suggestions.append("建议用户手动确认截止日期。")
        if float(todo.get("confidence", 0) or 0) < 0.65:
            issues.append(f"任务“{title}”置信度偏低。")
            suggestions.append("建议展示原文证据并要求用户确认。")
        if not todo.get("evidence"):
            issues.append(f"任务“{title}”缺少原文证据。")
    draft = action.get("draft")
    if draft and any(k in draft.get("body", "") for k in ["我保证", "一定完成", "立即发送"]):
        issues.append("草稿中包含过强承诺。")
        suggestions.append("建议改为更稳妥的表达。")
    risk_level = "high" if len(issues) >= 3 else "medium" if issues else "low"
    return {"risk_level": risk_level, "issues": issues, "suggestions": suggestions}


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_level": data.get("risk_level", "medium"),
        "issues": data.get("issues", []),
        "suggestions": data.get("suggestions", []),
    }
