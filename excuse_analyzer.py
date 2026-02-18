"""
Analyze excuse emails with Google Gemini (free API): extract reason for absence and suggest approve/reject.
Uses GEMINI_API_KEY from the environment. Get a free key at https://aistudio.google.com/apikey
Uses the google-genai SDK and gemini-3-flash-preview (free tier).
"""

from __future__ import annotations

import json
import os
from typing import Optional, TypedDict


class ExcuseAnalysis(TypedDict):
    reason: str
    suggestion: str  # "approve" or "reject"
    explanation: str


SYSTEM_PROMPT = """You are helping a math center coordinator evaluate emails from students/fellows who may be explaining an absence from a required session.

For each email sent to the math center (no attendance photo attached), you must:
1. Extract the reason the person gives for being absent (or state "No reason given" if unclear).
2. Suggest whether to APPROVE or REJECT the excuse based on the email content and the reason.
3. Give a brief explanation for your suggestion (one sentence).

Guidelines:
- Approve if the email clearly states a legitimate excuse (illness, family emergency, conflict, etc.) and appears to be from a student/fellow.
- Reject if the email is spam, unrelated, or does not clearly explain an absence.
- If the reason is vague or missing, lean toward reject unless the tone clearly indicates an excuse request.
- Respond only with valid JSON in this exact format, no other text:
{"reason": "...", "suggestion": "approve" or "reject", "explanation": "..."}"""


def analyze_excuse(
    email_body: str,
    sender_email: str = "",
    sender_name: str = "",
    api_key: Optional[str] = None,
    model: str = "gemini-3-flash-preview",
) -> ExcuseAnalysis:
    """
    Call Google Gemini to extract absence reason and get approve/reject suggestion.
    Returns dict with keys: reason, suggestion, explanation.
    Free API key: https://aistudio.google.com/apikey
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return {
            "reason": "(Gemini API key not set; set GEMINI_API_KEY to enable. Get a free key at https://aistudio.google.com/apikey)",
            "suggestion": "reject",
            "explanation": "Cannot analyze without API key.",
        }

    try:
        from google import genai
    except ImportError:
        return {
            "reason": "(install google-genai: pip install google-genai)",
            "suggestion": "reject",
            "explanation": "Gemini client not installed.",
        }

    client = genai.Client(api_key=key)
    who = sender_name or sender_email or "Unknown"
    user_content = f"""Sender: {who}
Email address: {sender_email or "unknown"}

Email body:
---
{email_body or "(empty)"}
---

Respond with JSON only: {{"reason": "...", "suggestion": "approve" or "reject", "explanation": "..."}}"""

    full_prompt = f"""{SYSTEM_PROMPT}

---

{user_content}"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
        )
        text = (response.text or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )
        data = json.loads(text)
        reason = data.get("reason", "") or "(none)"
        suggestion = (data.get("suggestion") or "reject").lower()
        if suggestion not in ("approve", "reject"):
            suggestion = "reject"
        explanation = data.get("explanation", "") or ""
        return {
            "reason": reason,
            "suggestion": suggestion,
            "explanation": explanation,
        }
    except json.JSONDecodeError as e:
        return {
            "reason": "(parse error)",
            "suggestion": "reject",
            "explanation": f"LLM response was not valid JSON: {e}",
        }
    except Exception as e:
        return {
            "reason": "(error)",
            "suggestion": "reject",
            "explanation": str(e)[:200],
        }
