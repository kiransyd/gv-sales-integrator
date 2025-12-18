from __future__ import annotations

import json
import logging
from typing import Any, Optional, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.settings import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


class LLMTransientError(LLMError):
    """Transient LLM errors (timeouts, 429/5xx, network) that should be retried."""


def _gemini_endpoint(model: str, api_key: str) -> str:
    # Using the public Generative Language API endpoint.
    # Docs commonly use v1beta; we keep it here for compatibility.
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


def _call_gemini(*, system: str, user: str) -> str:
    import time
    
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY not configured")

    url = _gemini_endpoint(settings.GEMINI_MODEL, settings.GEMINI_API_KEY)
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.3,  # Slightly higher for more thorough extraction
            "maxOutputTokens": 8192,  # Increased to ensure all fields complete
        },
    }

    logger.info("🤖 Calling Gemini LLM API. model=%s user_prompt_len=%d", settings.GEMINI_MODEL, len(user))
    start_time = time.time()
    
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        raise LLMTransientError(str(e)) from e
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429 or 500 <= code <= 599:
            raise LLMTransientError(f"Gemini HTTP {code}") from e
        raise

    elapsed = time.time() - start_time
    try:
        candidate = body["candidates"][0]
        result = candidate["content"]["parts"][0]["text"]
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        logger.info("✅ Gemini LLM response received. elapsed=%.2fs response_len=%d finish_reason=%s", elapsed, len(result), finish_reason)

        # Warn if response was truncated
        if finish_reason != "STOP":
            logger.warning("⚠️  Gemini response may be incomplete. finish_reason=%s", finish_reason)

        # Log full response for debugging (important for diagnosing empty fields)
        if len(result) > 2000:
            logger.info("LLM response (first 1000 chars): %s...", result[:1000])
            logger.info("LLM response (last 500 chars): ...%s", result[-500:])
        else:
            logger.info("LLM full response: %s", result)
        return result
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Unexpected Gemini response shape: {body}") from e


def _extract_json_object(text: str) -> str:
    """
    Best-effort extraction of a single JSON object from LLM output.
    Handles markdown code blocks (```json ... ```) and other wrappers.
    We still enforce strict validation after parsing.
    """
    s = text.strip()

    # Remove markdown code blocks
    if s.startswith("```"):
        # Find the closing ```
        end_marker = s.find("```", 3)
        if end_marker > 0:
            s = s[3:end_marker].strip()
            # Remove language identifier if present (e.g., "json")
            if s.startswith("json"):
                s = s[4:].strip()
            elif s.startswith("JSON"):
                s = s[4:].strip()

    # Clean up any remaining whitespace
    s = s.strip()

    # Extract JSON object - find matching braces
    start = s.find("{")
    if start < 0:
        return s

    # Find the matching closing brace by counting
    brace_count = 0
    end = -1
    for i in range(start, len(s)):
        if s[i] == "{":
            brace_count += 1
        elif s[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end = i
                break

    if end > start:
        return s[start : end + 1]

    # Fallback to rfind if brace matching failed
    end = s.rfind("}")
    if start >= 0 and end > start:
        return s[start : end + 1]

    return s


def _truncate(s: str, limit: int = 1200) -> str:
    s = s.strip()
    return s if len(s) <= limit else s[:limit] + "...(truncated)"


def generate_strict_json(
    *,
    model: type[T],
    system_prompt: str,
    user_prompt: str,
) -> T:
    """
    2-attempt flow:
    1) Ask for JSON-only
    2) If parse/validation fails, ask to repair with errors
    """
    import time
    
    logger.info("🔄 Generating strict JSON with LLM. model=%s", model.__name__)
    attempt1_start = time.time()
    
    raw1 = _call_gemini(system=system_prompt, user=user_prompt)
    json1 = _extract_json_object(raw1)
    logger.debug("Extracted JSON (first %d chars): %s", len(json1), json1[:500] if len(json1) > 500 else json1)
    try:
        obj1 = json.loads(json1)
        # Handle case where LLM wraps response in "properties" or other wrapper keys
        if isinstance(obj1, dict) and len(obj1) == 1:
            # Check if there's a single key that contains our data
            first_key = list(obj1.keys())[0]
            if isinstance(obj1[first_key], dict):
                # Convert null values in nested object too
                for key, value in obj1[first_key].items():
                    if value is None:
                        obj1[first_key][key] = ""
                # Try using the nested object
                try:
                    validated = model.model_validate(obj1[first_key])
                    elapsed = time.time() - attempt1_start
                    logger.info("✅ LLM JSON validation succeeded on attempt 1 (unwrapped from '%s'). elapsed=%.2fs", first_key, elapsed)
                    if hasattr(validated, 'model_dump'):
                        extracted = validated.model_dump()
                        logger.debug("LLM extracted values: %s", {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v) for k, v in extracted.items()})
                    return validated
                except ValidationError:
                    # Fall through to try root object
                    pass
        # Try validating root object as-is
        validated = model.model_validate(obj1)
        elapsed = time.time() - attempt1_start
        logger.info("✅ LLM JSON validation succeeded on attempt 1. elapsed=%.2fs", elapsed)
        # Log the actual extracted values for debugging
        if hasattr(validated, 'model_dump'):
            extracted = validated.model_dump()
            logger.debug("LLM extracted values: %s", {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v) for k, v in extracted.items()})
        return validated
    except (json.JSONDecodeError, ValidationError) as e1:
        elapsed1 = time.time() - attempt1_start
        logger.warning("⚠️  LLM JSON validation failed (attempt1, elapsed=%.2fs): %s", elapsed1, e1)

        logger.info("🔄 Attempting LLM JSON repair...")
        fix_system = system_prompt
        fix_user = (
            "Fix this JSON to match the schema exactly. Output JSON only.\n\n"
            f"Validation errors:\n{_truncate(str(e1))}\n\n"
            f"Invalid JSON:\n{json1}"  # Don't truncate JSON - LLM needs complete data to repair
        )
        attempt2_start = time.time()
        raw2 = _call_gemini(system=fix_system, user=fix_user)
        json2 = _extract_json_object(raw2)
        try:
            obj2 = json.loads(json2)
            # Convert null values to empty strings for string fields
            if isinstance(obj2, dict):
                for key, value in obj2.items():
                    if value is None:
                        obj2[key] = ""
            validated = model.model_validate(obj2)
            elapsed2 = time.time() - attempt2_start
            total_elapsed = time.time() - attempt1_start
            logger.info("✅ LLM JSON validation succeeded on attempt 2. attempt2=%.2fs total=%.2fs", elapsed2, total_elapsed)
            return validated
        except (json.JSONDecodeError, ValidationError) as e2:
            total_elapsed = time.time() - attempt1_start
            raise LLMError(f"LLM output did not match schema after repair (total_elapsed={total_elapsed:.2f}s): {e2}") from e2


def calendly_lead_intel(*, calendly_payload_subset: dict[str, Any]) -> BaseModel:
    from app.schemas.llm import CalendlyLeadIntel

    schema_hint = CalendlyLeadIntel.model_json_schema()
    
    system = (
        "You are a NO BS senior B2B SaaS SDR at GoVisually. "
        "Your task is to extract CRM-ready lead intelligence and demo qualification notes from the Calendly data below. "
        "### INSTRUCTIONS: "
        "- Use ONLY information stated or clearly implied by the Calendly data "
        "- Do NOT invent facts, assumptions, or browse the web "
        "- Use concise, internal sales language "
        "- Output MUST be valid, parseable JSON "
        "- Do NOT include markdown, HTML, commentary, or explanations "
        "- Output ONLY the JSON object"
    )
    
    # Format the Calendly data in the exact format the user's prompt expects
    invitee = calendly_payload_subset.get("invitee", {})
    demo = calendly_payload_subset.get("demo", {})
    qa_data = calendly_payload_subset.get("questions_and_answers", [])
    tracking = calendly_payload_subset.get("tracking", {})
    
    # Build the formatted Calendly data string matching the user's prompt format
    calendly_data_lines = []
    calendly_data_lines.append(f"Name of person booking demo: {invitee.get('name', '')}")
    calendly_data_lines.append(f"email: {invitee.get('email', '')}")
    
    # Add phone if available
    phone = invitee.get("phone", "")
    if phone:
        calendly_data_lines.append(f"phone: {phone}")
    
    # Format Q&A - handle both list and string formats
    if isinstance(qa_data, list):
        for idx, qa_item in enumerate(qa_data):
            if isinstance(qa_item, dict):
                q = qa_item.get("question", "")
                a = qa_item.get("answer", "")
                if q and a:
                    calendly_data_lines.append(f"Question: {q}")
                    calendly_data_lines.append(f"Answer: {a}")
    elif isinstance(qa_data, str) and qa_data.strip():
        # If it's a string, try to parse it or use as-is
        calendly_data_lines.append(f"Questions and Answers:\n{qa_data}")
    
    if demo.get("timezone"):
        calendly_data_lines.append(f"Timezone: {demo.get('timezone', '')}")
    if demo.get("start_time"):
        calendly_data_lines.append(f"Demo start time: {demo.get('start_time', '')}")
    
    # Add tracking/UTM data if available
    if tracking and isinstance(tracking, dict):
        utm_source = tracking.get("utm_source", "")
        utm_medium = tracking.get("utm_medium", "")
        utm_campaign = tracking.get("utm_campaign", "")
        if utm_source or utm_medium or utm_campaign:
            calendly_data_lines.append(f"Tracking: utm_source={utm_source}, utm_medium={utm_medium}, utm_campaign={utm_campaign}")
    
    calendly_data_formatted = "\n".join(calendly_data_lines)
    
    user = (
        "You are a NO BS senior B2B SaaS SDR at GoVisually. Your task is to extract CRM-ready lead intelligence and demo qualification notes from the Calendly data below.\n\n"
        "### INSTRUCTIONS:\n"
        "- Extract ALL available information from the Calendly data below\n"
        "- Use ONLY information stated or clearly implied by the Calendly data\n"
        "- Do NOT invent facts, assumptions, or browse the web\n"
        "- Use concise, internal sales language\n"
        "- Output MUST be valid, parseable JSON\n"
        "- Do NOT include markdown, HTML, commentary, or explanations\n"
        "- Output ONLY the JSON object\n"
        "- BE THOROUGH AND AGGRESSIVE: Extract EVERY piece of information available from the Q&A answers, name, email, timezone, and any other data provided\n"
        "- If you see ANY information in the data below, extract it - do not leave fields empty unless truly no information is available\n\n"
        "### CRITICAL ZOHO FORMATTING RULES (STRICT):\n"
        "- For any field that contains multiple points: Use REAL line breaks between numbered items\n"
        "- Do NOT use the characters \"\\n\"\n"
        "- Do NOT escape line breaks\n"
        "- Each numbered point MUST appear on its own line\n"
        "- Zoho must be able to render the text exactly as written\n\n"
        "### NAME RULES:\n"
        "- Extract first_name and last_name from the invitee name field\n"
        "- Split on spaces: first word = first_name, rest = last_name\n"
        "- If only one name is provided, use it as first_name and derive last_name from company_name\n"
        "- last_name must NEVER be empty - use company name or \".\" if needed\n\n"
        "### COMPANY RULES:\n"
        "- Extract company_name from the email domain (e.g., isabelle@leapzonestrategies.com → \"Leapzonestrategies\")\n"
        "- Remove common TLDs (.com, .co, .io, .net, .org)\n"
        "- Convert to Title Case\n"
        "- Derive company_website as https://{email_domain}\n"
        "- If the email domain is gmail.com, outlook.com, yahoo.com, or icloud.com, set company_website to \"\"\n"
        "- Extract company_type from Q&A answers (e.g., \"Branding/Design Agency\", \"SaaS Company\")\n\n"
        "### LOCATION INFERENCE RULES:\n"
        "- Infer location ONLY from the provided timezone\n"
        "- America/Los_Angeles → United States, California, Los Angeles\n"
        "- America/New_York → United States, New York, New York\n"
        "- Australia/Sydney → Australia, New South Wales, Sydney\n"
        "- If a value cannot be confidently inferred, use \"Unknown\"\n\n"
        "### COMPANY DESCRIPTION RULES:\n"
        "- Produce a ONE-LINE factual description combining: company_type + stated pain points + tools in use\n"
        "- Example: \"Branding/Design Agency that needs faster client approval workflows, currently using Trello and Adobe Creative Cloud\"\n"
        "- If insufficient data, use \"Not discussed\"\n\n"
        "### EXTRACTION RULES FOR Q&A:\n"
        "- Extract team_size from answers mentioning team size (e.g., \"2 to 5 team members\" → \"2-5\" or \"2 to 5 team members\")\n"
        "- Extract tools_in_use from answers mentioning tools (e.g., \"Trello\\nAdobe Creative Cloud\" → format as numbered list with line breaks)\n"
        "- Extract stated_pain_points from answers describing challenges (e.g., \"clients don't respond to comment replies\" → format as numbered list)\n"
        "- Extract stated_demo_objectives from answers about goals or what they want to achieve\n"
        "- Extract company_type from answers (e.g., \"Branding/Design Agency\")\n"
        "- Extract industry from answers if mentioned (e.g., \"Marketing\", \"Technology\", \"Healthcare\", \"Manufacturing\")\n"
        "- Extract referred_by from answers about how they heard about us (e.g., \"Search engine (Google, Bing)\", \"LinkedIn\", \"Referral from John\", etc.)\n"
        "- Extract phone number if mentioned in any Q&A answer (look for phone patterns like +1-xxx-xxx-xxxx, (xxx) xxx-xxxx, etc.)\n"
        "- Generate recommended_discovery_questions: 3-4 concise questions (max 2 lines per question) based on gaps in the information\n"
        "- Generate demo_focus_recommendations: 2-3 concise bullet points based on pain points and objectives\n"
        "- Create sales_rep_cheat_sheet: Brief summary (max 4-5 lines) of key facts for the sales rep\n\n"
        "### DATETIME RULES:\n"
        "- demo_datetime_utc must be ISO 8601 UTC with Z suffix (use the start_time exactly)\n"
        "- demo_datetime_local must be human-readable format: \"Wed, 16 Dec 2025 at 2:30 PM PST\" (use timezone to convert)\n\n"
        "### BANT RULES:\n"
        "- bant_budget_signal: Extract any budget mentions or infer from company size/type\n"
        "- bant_authority_signal: Extract decision-maker info from Q&A\n"
        "- bant_need_signal: Extract pain points and urgency from answers\n"
        "- bant_timing_signal: Extract timeline mentions or infer from demo booking\n"
        "- If a BANT element cannot be inferred, use \"Unknown\"\n\n"
        "### JSON STRUCTURE:\n"
        "You MUST return a JSON object with these exact keys and ACTUAL EXTRACTED VALUES (not schema definitions):\n"
        "{\n"
        '  "first_name": "extracted value or empty string",\n'
        '  "last_name": "extracted value or empty string",\n'
        '  "company_name": "extracted value or empty string",\n'
        '  "company_website": "extracted value or empty string",\n'
        '  "company_type": "extracted value or empty string",\n'
        '  "company_description": "extracted value or empty string",\n'
        '  "team_size": "extracted value or empty string",\n'
        '  "country": "extracted value or empty string",\n'
        '  "state_or_region": "extracted value or empty string",\n'
        '  "city": "extracted value or empty string",\n'
        '  "phone": "extracted value or empty string",\n'
        '  "industry": "extracted value or empty string",\n'
        '  "referred_by": "extracted value or empty string",\n'
        '  "tools_in_use": "extracted value or empty string",\n'
        '  "stated_pain_points": "extracted value or empty string",\n'
        '  "stated_demo_objectives": "extracted value or empty string",\n'
        '  "additional_notes": "extracted value or empty string",\n'
        '  "demo_datetime_utc": "extracted value or empty string",\n'
        '  "demo_datetime_local": "extracted value or empty string",\n'
        '  "bant_budget_signal": "extracted value or empty string",\n'
        '  "bant_authority_signal": "extracted value or empty string",\n'
        '  "bant_need_signal": "extracted value or empty string",\n'
        '  "bant_timing_signal": "extracted value or empty string",\n'
        '  "qualification_gaps": "extracted value or empty string",\n'
        '  "recommended_discovery_questions": "extracted value or empty string",\n'
        '  "demo_focus_recommendations": "extracted value or empty string",\n'
        '  "sales_rep_cheat_sheet": "extracted value or empty string"\n'
        "}\n\n"
        "### CALENDLY DATA:\n"
        f"{calendly_data_formatted}\n\n"
        "### CRITICAL: Return ACTUAL DATA VALUES, NOT SCHEMA DEFINITIONS\n"
        "You must return a JSON object with actual extracted values. For example:\n"
        "If the data contains: Name=\"Isabelle Mercier\", Email=\"isabelle@leapzonestrategies.com\", Q&A=\"What type of company are you? Answer: Branding/Design Agency\", \"Can you share the size of your team? Answer: 2 to 5 team members\", \"Are you using a project management or CRM tool? Answer: Trello, Adobe Creative Cloud\"\n"
        "Then return:\n"
        "{\n"
        '  "first_name": "Isabelle",\n'
        '  "last_name": "Mercier",\n'
        '  "company_name": "Leapzonestrategies",\n'
        '  "company_website": "https://leapzonestrategies.com",\n'
        '  "company_type": "Branding/Design Agency",\n'
        '  "team_size": "2 to 5 team members",\n'
        '  "tools_in_use": "1. Trello\\n2. Adobe Creative Cloud",\n'
        '  "stated_pain_points": "1. Clients don\'t respond to comment replies\\n2. Need clients to attentively review final proofs",\n'
        '  ... (all other fields with extracted values)\n'
        "}\n\n"
        "NOT a schema definition with \"properties\" or \"type\" fields. Return ONLY the data object with actual values extracted from the Calendly data above."
    )
    
    return generate_strict_json(model=CalendlyLeadIntel, system_prompt=system, user_prompt=user)


def readai_meddic(
    *,
    title: str,
    datetime_str: str,
    attendees: list[dict[str, Any]],
    summary: str,
    transcript: str,
) -> BaseModel:
    from app.schemas.llm import MeddicOutput

    schema_hint = MeddicOutput.model_json_schema()
    system = (
        "You are a NO BS style senior enterprise B2B SaaS sales analyst at GoVisually. "
        "Your task is to extract CRM-ready MEDDIC qualification data from the meeting transcript provided below. "
        "### INSTRUCTIONS: "
        "- Analyze the transcript to extract key sales intelligence. "
        "- Use ONLY information stated or clearly implied. Do NOT invent facts. "
        "- Use internal, concise sales language. "
        "- Output MUST be valid, parseable JSON. "
        "- Do not include markdown formatting (like ``````) or any text outside the JSON object."
    )
    
    # Truncate transcript if too long (Gemini has token limits ~32k tokens)
    # Strategy: Keep beginning (context, pain points) + end (decisions, next steps) + strategic samples from middle
    transcript_clean = transcript.strip()
    original_len = len(transcript_clean)
    
    if original_len > 50000:
        # For very long transcripts (50k+ chars), use smart sampling
        # Keep: first 10k (context) + 3 strategic samples from middle + last 12k (decisions)
        first_part = transcript_clean[:10000]
        last_part = transcript_clean[-12000:]
        middle = transcript_clean[10000:-12000]
        
        if len(middle) > 0:
            # Sample 3 chunks from middle at 25%, 50%, 75% positions
            chunk_size = min(3000, len(middle) // 4)  # ~3k chars per sample
            middle_samples = []
            for pos in [0.25, 0.5, 0.75]:
                idx = int(len(middle) * pos)
                sample = middle[idx:idx+chunk_size]
                if sample.strip():
                    middle_samples.append(sample.strip())
            
            if middle_samples:
                middle_str = "\n\n".join([f"[Sample from middle section {i+1}]\n{s}" for i, s in enumerate(middle_samples)])
                transcript_clean = f"{first_part}\n\n[--- Middle transcript (sampled) ---]\n\n{middle_str}\n\n[--- End of transcript ---]\n\n{last_part}"
            else:
                transcript_clean = f"{first_part}\n\n[--- Middle transcript truncated ---]\n\n{last_part}"
        else:
            transcript_clean = f"{first_part}\n\n[--- Middle transcript truncated ---]\n\n{last_part}"
        
        logger.info("Transcript truncated: %d -> %d chars (kept: first 10k + middle samples + last 12k)", original_len, len(transcript_clean))
    elif original_len > 30000:
        # For long transcripts (30-50k), keep first 12k + last 15k
        first_part = transcript_clean[:12000]
        last_part = transcript_clean[-15000:]
        transcript_clean = f"{first_part}\n\n[--- Middle transcript truncated ---]\n\n{last_part}"
        logger.info("Transcript truncated: %d -> %d chars", original_len, len(transcript_clean))
    elif original_len > 20000:
        # For medium-long (20-30k), keep first 10k + last 10k
        first_part = transcript_clean[:10000]
        last_part = transcript_clean[-10000:]
        transcript_clean = f"{first_part}\n\n[--- Middle transcript truncated ---]\n\n{last_part}"
        logger.info("Transcript truncated: %d -> %d chars", original_len, len(transcript_clean))
    elif original_len > 15000:
        # For medium (15-20k), keep first 8k + last 7k
        first_part = transcript_clean[:8000]
        last_part = transcript_clean[-7000:]
        transcript_clean = f"{first_part}\n\n[--- Middle transcript truncated ---]\n\n{last_part}"
    
    user = (
        "### FORMATTING RULES FOR LISTS:\n"
        "- For fields requesting a list (metrics, decision_criteria, decision_process, identified_pain, next_steps, risks), format the value as a SINGLE string.\n"
        "- You MUST use the newline character \"\\n\" to separate numbered items.\n"
        "- DO NOT just run items together.\n"
        "- Example correct output: \"1. Integration with Jira\\n2. SSO Requirement\\n3. Budget approval\"\n\n"
        "### JSON STRUCTURE:\n"
        "Map the analysis to the following JSON keys. If a section was not discussed, the value must be an empty string \"\".\n"
        "{\n"
        '  "metrics": "Success metrics or KPIs (String - Numbered list with \\n separators)",\n'
        '  "economic_buyer": "Names/roles of budget controllers or decision makers (String)",\n'
        '  "decision_criteria": "Technical or business requirements (String - Numbered list with \\n separators)",\n'
        '  "decision_process": "Steps/timeline for buying (String - Numbered list with \\n separators)",\n'
        '  "identified_pain": "Specific problems the prospect is facing (String - Numbered list with \\n separators)",\n'
        '  "champion": "Names/roles of enthusiastic supporters (String)",\n'
        '  "competition": "Other vendors or solutions mentioned (String)",\n'
        '  "next_steps": "Action items or follow-ups discussed (String - Numbered list with \\n separators)",\n'
        '  "risks": "Concerns, blockers, or potential issues (String - Numbered list with \\n separators)",\n'
        '  "confidence": "Qualification level: "Cold", "Warm", "Hot", or "Super-hot" (String)"\n'
        "}\n\n"
        "### FIELD DEFINITIONS:\n"
        "- metrics: Business outcomes, goals, or KPIs they want to achieve (e.g., 'reduce time to market', 'cut costs by X%')\n"
        "- economic_buyer: Person who controls budget/approves purchase (name, title, role)\n"
        "- decision_criteria: Factors they'll use to evaluate vendors (e.g., 'integration with Adobe', 'compliance features')\n"
        "- decision_process: Steps/timeline for making the decision (e.g., 'evaluate 3 vendors, decision by Q2')\n"
        "- identified_pain: Problems/pain points they're trying to solve (e.g., 'human error in compliance checks', 'slow approval process')\n"
        "- champion: Internal advocate who supports your solution (name, title, why they're a champion)\n"
        "- competition: Other vendors/solutions they're considering or currently using (e.g., 'Workfront', 'manual processes')\n"
        "- next_steps: Concrete action items discussed (e.g., 'send pricing', 'schedule technical demo')\n"
        "- risks: Potential blockers or concerns raised (e.g., 'budget constraints', 'integration challenges')\n"
        "- confidence: Overall qualification level based on engagement: 'Cold', 'Warm', 'Hot', or 'Super-hot'\n\n"
        f"### MEETING CONTEXT:\n"
        f"- Title: {title}\n"
        f"- Date/Time: {datetime_str}\n"
        f"- Attendees: {json.dumps(attendees, ensure_ascii=False)}\n"
        f"- Summary: {summary}\n\n"
        f"### TRANSCRIPT:\n{transcript_clean}\n\n"
        "Now extract ALL MEDDIC fields from the transcript above. Return JSON only (no markdown, no code blocks)."
    )
    return generate_strict_json(model=MeddicOutput, system_prompt=system, user_prompt=user)


