import pytest
from google.genai import errors

from app.config import get_settings
from app.extraction import extractor, ratelimit
from app.extraction.extractor import LLMUnavailable, _call_llm, _retry_seconds

DAILY = {
    "error": {
        "code": 429,
        "message": "You exceeded your current quota. Please retry in 20h39m9s.",
        "status": "RESOURCE_EXHAUSTED",
        "details": [
            {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
            {"retryDelay": "74349s"},
        ],
    }
}
PER_MINUTE = {
    "error": {
        "code": 429,
        "message": "Quota exceeded for GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
        "status": "RESOURCE_EXHAUSTED",
        "details": [{"retryDelay": "12s"}],
    }
}
BUSY = {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}}


@pytest.fixture(autouse=True)
def _models(monkeypatch):
    monkeypatch.setenv("GEMINI_MODELS", "m1,m2")
    get_settings.cache_clear()
    ratelimit._local_exhausted.clear()
    store: dict[str, float] = {}
    monkeypatch.setattr(extractor, "wait_for_slot", lambda m: None)
    monkeypatch.setattr(extractor, "mark_exhausted", lambda m, s: store.__setitem__(m, s))
    monkeypatch.setattr(extractor, "exhausted_for", lambda m: store.get(m, 0.0))
    yield store
    get_settings.cache_clear()


def fake(script):
    """script: {model: [outcome, ...]}; an outcome is a string or an APIError to raise."""
    calls = []

    def generate(model, *_):
        calls.append(model)
        out = script[model].pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    return generate, calls


def test_first_model_answers():
    gen, calls = fake({"m1": ["{}"]})
    res = _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None)
    assert res.model == "m1" and calls == ["m1"]


def test_daily_quota_marks_model_and_retries_same_email_on_next(_models):
    gen, calls = fake({"m1": [errors.ClientError(429, DAILY)], "m2": ["{}"]})
    res = _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None)
    assert res.model == "m2" and calls == ["m1", "m2"]
    assert _models["m1"] == 74349  # reset time taken from the error's own retry delay


def test_exhausted_model_is_skipped_by_later_calls(_models):
    _models["m1"] = 5000
    gen, calls = fake({"m2": ["{}"]})
    assert _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None).model == "m2"
    assert calls == ["m2"]


def test_503_backs_off_then_moves_to_next_model():
    slept = []
    gen, calls = fake({"m1": [errors.ServerError(503, BUSY)] * 3, "m2": ["{}"]})
    res = _call_llm("a", "b", "c", generate=gen, sleep=slept.append)
    assert calls == ["m1", "m1", "m1", "m2"] and res.model == "m2"
    assert slept == [2.0, 4.0]


def test_503_recovers_on_same_model():
    gen, calls = fake({"m1": [errors.ServerError(503, BUSY), "{}"]})
    assert _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None).model == "m1"


def test_per_minute_429_just_waits_and_retries_same_model():
    slept = []
    gen, calls = fake({"m1": [errors.ClientError(429, PER_MINUTE), "{}"]})
    res = _call_llm("a", "b", "c", generate=gen, sleep=slept.append)
    assert res.model == "m1" and slept == [12.0]


def test_all_exhausted_raises_retryable_with_wait_time():
    gen, _ = fake({"m1": [errors.ClientError(429, DAILY)], "m2": [errors.ClientError(429, DAILY)]})
    with pytest.raises(LLMUnavailable) as e:
        _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None)
    assert e.value.retry_after == 74349


def test_retry_seconds_from_message_when_no_details():
    exc = errors.ClientError(429, {"error": {"code": 429, "message": "retry in 1h2m3.5s"}})
    assert _retry_seconds(exc) == 3723.5


def test_azure_entry_uses_azure_generator_and_429_waits(monkeypatch):
    from app.extraction.extractor import LLMError

    monkeypatch.setenv("GEMINI_MODELS", "azure:gpt,m2")
    get_settings.cache_clear()
    slept = []
    gen, calls = fake({"azure:gpt": [LLMError(429, "rate", 7.0), "{}"]})
    res = _call_llm("a", "b", "c", generate=gen, sleep=slept.append)
    assert res.model == "azure:gpt" and slept == [7.0]


def test_azure_down_falls_through_to_gemini(monkeypatch):
    from app.extraction.extractor import LLMError

    monkeypatch.setenv("GEMINI_MODELS", "azure:gpt,m2")
    get_settings.cache_clear()
    gen, calls = fake({"azure:gpt": [LLMError(503, "x")] * 3, "m2": ["{}"]})
    assert _call_llm("a", "b", "c", generate=gen, sleep=lambda s: None).model == "m2"


def test_azure_http_payload(monkeypatch):
    import httpx

    from app.extraction import extractor

    monkeypatch.setenv("AZURE_ENDPOINT", "https://r.openai.azure.com/openai/v1/")
    monkeypatch.setenv("AZURE_API_KEY", "k")
    get_settings.cache_clear()
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update(url=url, json=json, headers=headers)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr(extractor.httpx, "post", fake_post)
    assert extractor._generate("azure:dep", "a", "b", "c") == "{}"
    assert seen["url"] == "https://r.openai.azure.com/openai/v1/chat/completions"
    assert seen["json"]["model"] == "dep"
    assert seen["headers"] == {"api-key": "k", "Authorization": "Bearer k"}
