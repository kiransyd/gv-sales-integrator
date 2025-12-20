"""
Text formatting utilities for Zoho notes and other plain text outputs.

Zoho Notes don't support Markdown, so we convert Markdown to plain text.
"""

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


def extract_domain_from_email(email: str) -> str:
    """
    Extract domain from email address.
    Example: "john@acme.com" -> "acme.com"
    """
    if not email or "@" not in email:
        return ""
    return email.split("@")[1].strip().lower()


def markdown_to_plain_text(markdown_text: str) -> str:
    """
    Convert Markdown to plain text format suitable for Zoho Notes.
    
    Zoho Notes don't render Markdown, so we convert:
    - Headers (##, ###) to uppercase text with separators
    - Bold (**text**) to uppercase or plain text
    - Bullet points (-) to plain bullet points
    - Links ([text](url)) to plain text with URL
    
    Args:
        markdown_text: Markdown-formatted text
        
    Returns:
        Plain text formatted for readability
    """
    lines = markdown_text.split("\n")
    result = []
    
    for line in lines:
        # Headers: ## Header -> HEADER
        if line.startswith("## "):
            header = line[3:].strip()
            result.append("")
            result.append(header.upper())
            result.append("=" * len(header))
        elif line.startswith("### "):
            header = line[4:].strip()
            result.append("")
            result.append(header.upper())
            result.append("-" * len(header))
        # Bold: **text** -> TEXT: or just text (depending on context)
        elif "**" in line:
            # Replace **text** with TEXT (for labels) or just text (for values)
            import re
            # Pattern: **Label:** value -> LABEL: value
            line = re.sub(r'\*\*([^*]+):\*\*', r'\1:', line)
            # Pattern: **text** (not followed by :) -> text (uppercase if it's a label)
            line = re.sub(r'\*\*([^*]+)\*\*', lambda m: m.group(1).upper() if len(m.group(1)) < 30 else m.group(1), line)
            result.append(line)
        # Bullet points: - item -> • item
        elif line.strip().startswith("- "):
            result.append("  • " + line.strip()[2:])
        # Empty lines
        elif not line.strip():
            result.append("")
        # Regular text
        else:
            result.append(line)
    
    # Clean up multiple consecutive empty lines
    cleaned = []
    prev_empty = False
    for line in result:
        if not line.strip():
            if not prev_empty:
                cleaned.append("")
            prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False
    
    return "\n".join(cleaned).strip()


def format_zoho_note_plain_text(
    title: str = "",
    sections: list[dict[str, str | list[str]]] | None = None,
    footer: str = "",
) -> str:
    """
    Format a Zoho note as plain text with clear sections.
    
    Args:
        title: Main title (will be uppercase)
        sections: List of dicts with 'title' and 'content' or 'items'
        footer: Footer text (e.g., links)
        
    Returns:
        Plain text formatted note
    """
    parts = []
    
    if title:
        parts.append(title.upper())
        parts.append("=" * len(title))
        parts.append("")
    
    if sections:
        for section in sections:
            section_title = section.get("title", "")
            content = section.get("content", "")
            items = section.get("items", [])
            
            if section_title:
                parts.append(section_title.upper())
                parts.append("-" * len(section_title))
                parts.append("")
            
            if content:
                parts.append(content)
                parts.append("")
            
            if items:
                for item in items:
                    if isinstance(item, dict):
                        # Dict item: {"label": "Label", "value": "Value"}
                        label = item.get("label", "")
                        value = item.get("value", "")
                        if label and value:
                            parts.append(f"{label.upper()}: {value}")
                        elif label:
                            # Just a label (section header within section)
                            parts.append(f"{label.upper()}:")
                        elif value:
                            # Just a value (for bullet points)
                            parts.append(f"  • {value}")
                    else:
                        # String item
                        parts.append(f"  • {item}")
                parts.append("")
    
    if footer:
        parts.append("")
        parts.append(footer)
    
    return "\n".join(parts).strip()

