import json
import logging
import re
import time
from typing import NamedTuple

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.extraction.fallback import regex_extract
from app.extraction.ratelimit import exhausted_for, mark_exhausted, wait_for_slot
from app.profile import get_profile

log = logging.getLogger(__name__)

REFUSED_MODEL = "refused:content_filter"  # recorded as the model when every model refused


class LLMUnavailable(Exception):
    """No Gemini model could answer (all exhausted or down). Callers retry later."""

    def __init__(self, message: str, retry_after: float = 60.0):
        super().__init__(message)
        self.retry_after = retry_after


class LLMRefused(Exception):
    """Every model tried refused this input (e.g. Azure's content filter). Not retryable."""


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


def _is_content_filter(exc) -> bool:
    text = str(exc).lower()
    return "content management policy" in text or "content_filter" in text


def _is_daily_quota(exc) -> bool:  # Gemini only; Azure has no daily cap
    return "PerDay" in str(exc)


def _azure_raw(deployment: str, system: str, contents: str) -> str:
    """Azure AI Foundry / Azure OpenAI through the OpenAI-compatible v1 endpoint."""
    settings = get_settings()
    url = settings.azure_endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": contents},
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


def _gemini_raw(model: str, system: str, contents: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_settings().gemini_api_key)
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    return resp.text or ""


def _raw(model: str, system: str, contents: str) -> str:
    if model.startswith("azure:"):
        return _azure_raw(model.removeprefix("azure:"), system, contents)
    return _gemini_raw(model, system, contents)


def _generate(model: str, sender: str, subject: str, body: str) -> str:
    return _raw(model, get_profile().system_prompt, f"From: {sender}\nSubject: {subject}\n\n{body}")


def _generate_batch(model: str, emails: list[dict]) -> str:
    items = [
        {"id": str(i), "from": e["from"], "subject": e["subject"], "body": e["body"]}
        for i, e in enumerate(emails)
    ]
    return _raw(model, get_profile().batch_prompt, json.dumps(items, ensure_ascii=False))


def _failover(call, sleep=time.sleep) -> LLMResult:
    """Run `call(model) -> str` against the models in LLM_MODELS order; fail over per the rules.

    - daily-quota 429: mark the model exhausted in Redis until its reset, try the next model
    - 503/5xx: short backoff and retry, then try the next model
    - per-minute 429: wait the suggested time and retry the same model
    - every model exhausted or failing: raise LLMUnavailable (the task is retried later)
    """
    from google.genai import errors

    models = get_settings().gemini_model_list
    soonest: float | None = None
    last_error = "no models configured"
    tried = refused = 0

    for model in models:
        wait = exhausted_for(model)
        if wait > 0:
            soonest = wait if soonest is None else min(soonest, wait)
            continue
        tried += 1
        server_tries = minute_waits = 0
        while True:
            wait_for_slot(model)
            try:
                return LLMResult(call(model), model)
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
                        mark_exhausted(model, 60)  # short cooldown: skip it for a minute
                        break
                    sleep(SERVER_BACKOFF * 2 ** (server_tries - 1))
                    continue
                if code == 400 and _is_content_filter(exc):
                    refused += 1
                    log.warning("%s refused the input (content filter); trying next model", model)
                    break
                raise LLMUnavailable(last_error) from exc

    if tried and refused == tried:
        raise LLMRefused(last_error)
    raise LLMUnavailable(
        f"all models exhausted or unavailable ({last_error})",
        retry_after=soonest if soonest is not None else 60.0,
    )


def _call_llm(sender, subject, body, generate=_generate, sleep=time.sleep) -> LLMResult:
    return _failover(lambda model: generate(model, sender, subject, body), sleep)


def _call_llm_batch(emails, generate=_generate_batch, sleep=time.sleep) -> LLMResult:
    """One request carrying several emails (saves requests on quota-limited Gemini)."""
    return _failover(lambda model: generate(model, emails), sleep)


def available_models(models: list[str]) -> list[str]:
    """Models not currently marked exhausted or cooling down, in order."""
    return [m for m in models if exhausted_for(m) <= 0]


def default_batch_size(models: list[str]) -> int:
    """Emails per request in auto mode, from the model that is first in line."""
    settings = get_settings()
    if models and models[0].startswith("azure:"):
        return max(settings.azure_batch_size, 1)
    return max(settings.gemini_batch_size, 1)


def _with_regex(lead: BaseModel, sender: str, body: str) -> BaseModel:
    fb = regex_extract(sender, body)
    return lead.model_copy(update={k: getattr(lead, k) or v for k, v in fb.items()})


def extract_lead_with_model(
    sender: str, subject: str, body: str, llm=_call_llm
) -> tuple[BaseModel, str | None]:
    """LLM extraction validated by Pydantic; retries once, then falls back to regex.

    Returns the lead and the model that answered (None if the LLM output never validated).
    `llm` may return a plain string (tests) or an LLMResult.
    """
    Lead = get_profile().model
    model = None
    for attempt in (1, 2):
        try:
            try:
                out = llm(sender, subject, body)
            except LLMRefused as exc:
                log.warning("input refused by every model: %s", exc)
                lead = Lead(confidence=0.0)
                model = REFUSED_MODEL
                break
            text, used = (out.text, out.model) if isinstance(out, LLMResult) else (out, None)
            lead = Lead.model_validate_json(text)
            model = used
            break
        except (ValidationError, ValueError) as exc:
            log.warning("extraction attempt %s failed: %s", attempt, exc)
    else:
        lead = Lead(confidence=0.0)

    return _with_regex(lead, sender, body), model


def extract_lead(sender: str, subject: str, body: str, llm=_call_llm) -> BaseModel:
    return extract_lead_with_model(sender, subject, body, llm)[0]


def extract_leads_batch(
    emails: list[dict], llm_batch=_call_llm_batch, llm=_call_llm
) -> list[tuple[BaseModel, str | None]]:
    """Extract several emails with one request.

    Each result is matched back by id. Any email the model skipped or returned invalid
    output for is re-done on its own, so a bad batch never loses or mixes up a lead.
    """
    Lead = get_profile().model
    results: list[tuple[BaseModel, str | None] | None] = [None] * len(emails)
    out, data, why = None, [], ""
    try:
        out = llm_batch(emails)
        data = json.loads(out.text)
        if isinstance(data, dict):  # JSON mode (Azure) can only return an object
            data = next((v for v in data.values() if isinstance(v, list)), [])
        if not isinstance(data, list):
            data, why = [], "response was not a list"
    except LLMRefused as exc:
        data, why = [], f"a model refused the batch ({exc}); redoing emails one by one"
    except (ValueError, TypeError) as exc:
        data, why = [], f"response was not valid JSON ({exc})"
    for item in data:
        try:
            idx = int(item.get("id"))
            if not 0 <= idx < len(emails) or results[idx] is not None:
                continue
            lead = Lead.model_validate(item)
        except (AttributeError, TypeError, ValueError, ValidationError):
            continue
        e = emails[idx]
        results[idx] = (_with_regex(lead, e["from"], e["body"]), out.model)
    if not any(results):
        snippet = (out.text[:200] if out else "").replace("\n", " ")
        log.warning("batch of %s unusable: %s %r", len(emails), why or "no valid items", snippet)
    for idx, e in enumerate(emails):
        if results[idx] is None:
            log.warning("batch item %s missing or invalid; extracting it alone", idx)
            results[idx] = extract_lead_with_model(e["from"], e["subject"], e["body"], llm)
    return results  # type: ignore[return-value]
