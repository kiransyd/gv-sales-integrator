from __future__ import annotations

from typing import Any


def numbered_bullets(items: list[str]) -> str:
    cleaned = [i.strip() for i in items if i and i.strip()]
    if not cleaned:
        return ""
    return "\n".join(f"{idx}. {val}" for idx, val in enumerate(cleaned, start=1))


def qa_to_text(qa: Any) -> str:
    """
    Calendly questions_and_answers is usually a list of {question, answer}.
    """
    if not isinstance(qa, list):
        return ""
    lines: list[str] = []
    for item in qa:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "").strip()
        a = str(item.get("answer") or "").strip()
        if not q and not a:
            continue
        if q and a:
            lines.append(f"{q}: {a}")
        elif q:
            lines.append(q)
        else:
            lines.append(a)
    return numbered_bullets(lines)



