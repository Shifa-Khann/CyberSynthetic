"""
engine/llm.py
LLM client: one client, JSON mode, retry once, cache, template fallback.
Uses the OpenAI-compatible Gemini endpoint (or OpenRouter secondary).
NEVER sends raw data rows — only column names, stats, and facts.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
from typing import Any

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

_CACHE_DIR = pathlib.Path("cache")
_CACHE_DIR.mkdir(exist_ok=True)


def _is_llm_enabled() -> bool:
    return os.getenv("USE_LLM", "true").lower() in ("1", "true", "yes")


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def _cache_load(key: str) -> dict | None:
    path = _CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_save(key: str, data: dict) -> None:
    path = _CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_client():
    """Lazily build the OpenAI-compatible client."""
    try:
        from openai import OpenAI
        api_key = os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        if not api_key:
            return None
        return OpenAI(api_key=api_key, base_url=base_url)
    except Exception:
        return None


def _llm_call(prompt: str, system: str = "", temperature: float = 0.2) -> str | None:
    """
    Make one LLM call with retry. Returns text response or None on failure.
    Uses cache to avoid redundant calls.
    """
    if not _is_llm_enabled():
        return None

    cache_key = _cache_key(system + prompt)
    cached = _cache_load(cache_key)
    if cached is not None:
        return cached.get("response")

    client = _get_client()
    if client is None:
        return None

    model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(2):  # retry once
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
            )
            text = resp.choices[0].message.content
            _cache_save(cache_key, {"response": text})
            return text
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                return None
    return None


# ──────────────────────────────────────────────
# High-level jobs
# ──────────────────────────────────────────────

def plan_from_nl(nl_request: str, fallback_preset: str = "medium_full") -> dict:
    """
    Convert a natural-language request to a Plan dict.
    Falls back to a preset if LLM is off or fails.
    """
    from engine.plan import PRESETS

    system = (
        "You are a cybersecurity data generation planner. "
        "Output ONLY a valid JSON object matching this schema:\n"
        "{ mode, seed, duration_days, users, devices, ratios:{normal,suspicious,malicious}, "
        "difficulty, domains:[], scenarios:[], language, generate_documents, use_llm, "
        "calibration_profile }. "
        "Numbers only for IDs. No extra keys."
    )
    prompt = f"Generate a plan JSON for: {nl_request}"

    resp = _llm_call(prompt, system=system)
    if resp:
        try:
            # Extract JSON block
            match = re.search(r"\{.*\}", resp, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data
        except Exception:
            pass

    # Fallback: return preset
    return PRESETS.get(fallback_preset, PRESETS["small_auth"])


def generate_incident_narrative(facts: dict, language: str = "en") -> str:
    """
    Generate an incident narrative from structured facts dict.
    Facts must NOT include raw rows — only incident metadata, counts, and timestamps.
    """
    if language == "ur":
        system = (
            "آپ ایک سائبر سیکیورٹی ماہر ہیں۔ درج ذیل واقعے کے حقائق سے ایک اردو رپورٹ لکھیں۔ "
            "تمام آئی ڈی اور آئی پی پتے بالکل وہی رکھیں جو دیے گئے ہیں۔"
        )
        prompt = f"واقعے کی تفصیلات:\n{json.dumps(facts, ensure_ascii=False, indent=2)}"
    else:
        system = (
            "You are a cybersecurity incident response analyst. "
            "Write a concise English incident narrative (150-250 words) based on the facts below. "
            "Preserve all IDs, IPs, and timestamps exactly as given."
        )
        prompt = f"Incident facts:\n{json.dumps(facts, ensure_ascii=False, indent=2)}"

    resp = _llm_call(prompt, system=system)
    if resp:
        # Validate: if Urdu, must contain Urdu script
        if language == "ur" and not re.search(r"[\u0600-\u06FF]", resp):
            return _fallback_narrative(facts, language)
        return resp

    return _fallback_narrative(facts, language)


def _fallback_narrative(facts: dict, language: str = "en") -> str:
    """Template-based incident narrative without LLM."""
    inc_id = facts.get("incident_id", "INC-???")
    sev = facts.get("severity", "unknown")
    start = facts.get("start_time", "unknown")
    tactics = facts.get("mitre_tactics", "")
    victim = facts.get("victim_user_id", "unknown")

    if language == "ur":
        return (
            f"واقعہ {inc_id}: {sev} شدت کا سیکیورٹی واقعہ {start} کو رجسٹر ہوا۔ "
            f"متاثرہ صارف: {victim}۔ MITRE حکمت عملی: {tactics}۔ "
            f"تمام متعلقہ الرٹس اس واقعے سے منسلک ہیں۔"
        )
    return (
        f"Incident {inc_id} (severity: {sev}) was detected starting at {start}. "
        f"Victim user: {victim}. MITRE tactics: {tactics}. "
        f"All related alerts have been correlated into this incident."
    )


def generate_phishing_body(subject: str) -> str:
    """Generate a synthetic phishing email body. No real payload."""
    system = (
        "Generate a realistic-looking but clearly synthetic phishing email body for a cybersecurity dataset. "
        "Add the disclaimer '[SYNTHETIC - FOR TRAINING DATA ONLY]' at the end. "
        "No real links, credentials, or working payloads."
    )
    prompt = f"Subject: {subject}"
    resp = _llm_call(prompt, system=system)
    if resp:
        return resp
    return f"[SYNTHETIC PHISHING BODY - Subject: {subject}] [SYNTHETIC - FOR TRAINING DATA ONLY]"


def nl_to_sql(
    nl_query: str,
    schema_desc: str,
    examples: list[dict] | None = None,
) -> str | None:
    """
    Convert NL query to SQL SELECT (read-only). Returns SQL string or None.
    """
    system = (
        "You are a SQL expert. Convert the natural language question to a single SQL SELECT statement. "
        "Only output the SQL with no explanation. Include LIMIT 1000. "
        "The database is read-only SQLite. Never use INSERT, UPDATE, DELETE, DROP, or ATTACH."
    )
    ex_str = ""
    if examples:
        ex_str = "\n\nExamples:\n" + "\n".join(
            f"Q: {e['q']}\nSQL: {e['sql']}" for e in examples
        )
    prompt = f"Schema:\n{schema_desc}{ex_str}\n\nQuestion: {nl_query}"
    return _llm_call(prompt, system=system)
