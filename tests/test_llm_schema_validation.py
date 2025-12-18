from __future__ import annotations

import app.services.llm_service as llm
from app.schemas.llm import CalendlyLeadIntel


def test_generate_strict_json_repairs_invalid_output(monkeypatch):
    outputs = iter(
        [
            '{"one_line_summary": 123, "use_case": "x", "stated_pain_points": "", "stated_goals": "", "risks_or_gaps": "", "bant_signal": "", "confidence": "High"}',
            '{"one_line_summary": "ok", "use_case": "x", "stated_pain_points": "", "stated_goals": "", "risks_or_gaps": "", "bant_signal": "", "confidence": "High"}',
        ]
    )

    monkeypatch.setattr(llm, "_call_gemini", lambda system, user: next(outputs))

    out = llm.generate_strict_json(model=CalendlyLeadIntel, system_prompt="s", user_prompt="u")
    assert out.one_line_summary == "ok"




