import json
import logging
import re
import time
from typing import NamedTuple

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.extraction.fallback import regex_extract
from app.extraction.ratelimit import exhausted_for, mark_exhausted, wait_for_slot
from app.extraction.schema import Lead

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You extract structured data from inbound sales inquiries. "
    "Reply with a single JSON object matching this schema and nothing else:\n"
    f"{json.dumps(Lead.model_json_schema())}\n"
    "Use null for unknown fields. Set confidence between 0 and 1 for how sure you are."
)


class LLMUnavailable(Exception):
    """No Gemini model could answer (all exhausted or down). Callers retry later."""

    def __init__(self, message: str, retry_after: float = 60.0):
        super().__init__(message)
        self.retry_after = retry_after


class LLMError(Exception):
    """Provider-neutral API failure (used for Azure; Gemini errors are read directly)."""

    def __init__(self, code: int, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class LLMResult(NamedTuple):
    text: str
    model: str | None = None


SERVER_RETRIES = 3  # attempts per model on 5xx before moving to the next model
SERVER_BACKOFF = 2.0  # seconds; doubles each attempt
MINUTE_WAITS = 5  # per-minute 429s waited out per model before moving on


def _retry_seconds(exc) -> float | None:
    """Retry delay Google put in the error: RetryInfo.retryDelay, else 'retry in 1h2m3.4s'."""
    body = exc.details if isinstance(exc.details, dict) else {}
    details = body.get("error", {}).get("details", [])
    for d in details:
        delay = d.get("retryDelay")
        if delay:
            m = re.fullmatch(r"([\d.]+)s", str(delay))
            if m:
                return float(m.group(1))
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", str(exc))
    if m and any(m.groups()):
        h, mi, sec = (float(g) if g else 0.0 for g in m.groups())
        return h * 3600 + mi * 60 + sec
    return None


def _is_daily_quota(exc) -> bool:  # Gemini only; Azure has no daily cap
    return "PerDay" in str(exc)


def _generate_azure(deployment: str, sender: str, subject: str, body: str) -> str:
    """Azure AI Foundry / Azure OpenAI through the OpenAI-compatible v1 endpoint."""
    settings = get_settings()
    url = settings.azure_endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"From: {sender}\nSubject: {subject}\n\n{body}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    for attempt in (1, 2):
        try:
            # Foundry endpoints accept the key as a Bearer token, classic Azure OpenAI as api-key.
            headers = {
                "api-key": settings.azure_api_key,
                "Authorization": f"Bearer {settings.azure_api_key}",
            }
            r = httpx.post(url, json=payload, headers=headers, timeout=60)
        except httpx.TransportError as exc:
            raise LLMError(503, f"azure transport error: {exc}") from exc
        if r.status_code == 400 and attempt == 1 and "temperature" in r.text:
            payload.pop("temperature")  # some newer models only accept the default
            continue
        break
    if r.status_code != 200:
        try:
            retry = float(r.headers.get("retry-after", ""))
        except ValueError:
            retry = None
        raise LLMError(r.status_code, f"azure {r.status_code}: {r.text[:300]}", retry)
    return r.json()["choices"][0]["message"]["content"] or ""


def _generate(model: str, sender: str, subject: str, body: str) -> str:
    if model.startswith("azure:"):
        return _generate_azure(model.removeprefix("azure:"), sender, subject, body)
    return _generate_gemini(model, sender, subject, body)


def _generate_gemini(model: str, sender: str, subject: str, body: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_settings().gemini_api_key)
    resp = client.models.generate_content(
        model=model,
        contents=f"From: {sender}\nSubject: {subject}\n\n{body}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    return resp.text or ""


def _call_llm(sender, subject, body, generate=_generate, sleep=time.sleep) -> LLMResult:
    """Ask the models in GEMINI_MODELS order; fail over per the rules below.

    - daily-quota 429: mark the model exhausted in Redis until its reset, try the next model
    - 503/5xx: short backoff and retry, then try the next model
    - per-minute 429: wait the suggested time and retry the same model
    - every model exhausted or failing: raise LLMUnavailable (the task is retried later)
    """
    from google.genai import errors

    models = get_settings().gemini_model_list
    soonest: float | None = None
    last_error = "no models configured"

    for model in models:
        wait = exhausted_for(model)
        if wait > 0:
            soonest = wait if soonest is None else min(soonest, wait)
            continue
        server_tries = minute_waits = 0
        while True:
            wait_for_slot(model)
            try:
                return LLMResult(generate(model, sender, subject, body), model)
            except (errors.APIError, LLMError) as exc:
                last_error = f"{model}: {exc}"
                code = exc.code
                hint = exc.retry_after if isinstance(exc, LLMError) else _retry_seconds(exc)
                if code == 429 and isinstance(exc, errors.APIError) and _is_daily_quota(exc):
                    reset = hint or 3600.0
                    mark_exhausted(model, reset)
                    soonest = reset if soonest is None else min(soonest, reset)
                    log.warning("%s daily quota spent; skipping it for %.0fs", model, reset)
                    break
                if code == 429:
                    minute_waits += 1
                    if minute_waits > MINUTE_WAITS:
                        break
                    sleep(min(hint or 20.0, 60.0))
                    continue
                if code >= 500:
                    server_tries += 1
                    if server_tries >= SERVER_RETRIES:
                        log.warning("%s unavailable (%s); trying next model", model, code)
                        break
                    sleep(SERVER_BACKOFF * 2 ** (server_tries - 1))
                    continue
                raise LLMUnavailable(last_error) from exc

    raise LLMUnavailable(
        f"all Gemini models exhausted or unavailable ({last_error})",
        retry_after=soonest if soonest is not None else 60.0,
    )


def extract_lead_with_model(
    sender: str, subject: str, body: str, llm=_call_llm
) -> tuple[Lead, str | None]:
    """LLM extraction validated by Pydantic; retries once, then falls back to regex.

    Returns the lead and the model that answered (None if the LLM output never validated).
    `llm` may return a plain string (tests) or an LLMResult.
    """
    model = None
    for attempt in (1, 2):
        try:
            out = llm(sender, subject, body)
            text, used = (out.text, out.model) if isinstance(out, LLMResult) else (out, None)
            lead = Lead.model_validate_json(text)
            model = used
            break
        except (ValidationError, ValueError) as exc:
            log.warning("extraction attempt %s failed: %s", attempt, exc)
    else:
        lead = Lead(confidence=0.0)

    fb = regex_extract(sender, body)
    lead = lead.model_copy(update={k: getattr(lead, k) or v for k, v in fb.items()})
    return lead, model


def extract_lead(sender: str, subject: str, body: str, llm=_call_llm) -> Lead:
    return extract_lead_with_model(sender, subject, body, llm)[0]
