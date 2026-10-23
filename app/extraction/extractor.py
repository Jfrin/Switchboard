import json
import logging

from pydantic import ValidationError

from app.config import get_settings
from app.extraction.fallback import regex_extract
from app.extraction.ratelimit import wait_for_slot
from app.extraction.schema import Lead

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You extract structured data from inbound sales inquiries. "
    "Reply with a single JSON object matching this schema and nothing else:\n"
    f"{json.dumps(Lead.model_json_schema())}\n"
    "Use null for unknown fields. Set confidence between 0 and 1 for how sure you are."
)


class LLMUnavailable(Exception):
    """Gemini API error (rate limit, outage). Celery retries the task with backoff."""


def _call_llm(sender: str, subject: str, body: str) -> str:
    from google import genai
    from google.genai import errors, types

    settings = get_settings()
    wait_for_slot()
    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"From: {sender}\nSubject: {subject}\n\n{body}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    except errors.APIError as exc:
        raise LLMUnavailable(str(exc)) from exc
    return resp.text or ""


def extract_lead(sender: str, subject: str, body: str, llm=_call_llm) -> Lead:
    """LLM extraction validated by Pydantic; retries once, then falls back to regex."""
    for attempt in (1, 2):
        try:
            lead = Lead.model_validate_json(llm(sender, subject, body))
            break
        except (ValidationError, ValueError) as exc:
            log.warning("extraction attempt %s failed: %s", attempt, exc)
    else:
        lead = Lead(confidence=0.0)

    fb = regex_extract(sender, body)
    return lead.model_copy(
        update={k: getattr(lead, k) or v for k, v in fb.items()}
    )
