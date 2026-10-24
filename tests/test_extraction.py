import json

from app.extraction.extractor import extract_lead
from app.extraction.fallback import regex_extract


def test_regex_fallback():
    out = regex_extract("jane.doe@acme.com", "Call me on +65 6123 4567")
    assert out["email"] == "jane.doe@acme.com"
    assert out["domain"] == "acme.com"
    assert out["phone"].startswith("+65")


def test_extract_valid_llm_output():
    payload = json.dumps({"company": "Acme", "intent": "pricing", "confidence": 0.9})
    lead = extract_lead("jane@acme.com", "Pricing", "body", llm=lambda *a: payload)
    assert lead.company == "Acme"
    assert lead.domain == "acme.com"


def test_retry_once_then_succeed():
    calls = []

    def flaky(*_):
        calls.append(1)
        return "not json" if len(calls) == 1 else json.dumps({"confidence": 0.8})

    lead = extract_lead("jane@acme.com", "s", "b", llm=flaky)
    assert len(calls) == 2 and lead.confidence == 0.8


def test_two_failures_yield_zero_confidence():
    lead = extract_lead("jane@acme.com", "s", "b", llm=lambda *_: "garbage")
    assert lead.confidence == 0.0
    assert lead.email == "jane@acme.com"


def test_model_is_returned_with_llm_result():
    from app.extraction.extractor import LLMResult, extract_lead_with_model

    lead, model = extract_lead_with_model(
        "jane@acme.com", "s", "b", llm=lambda *_: LLMResult('{"confidence": 0.9}', "m1")
    )
    assert model == "m1" and lead.confidence == 0.9


def test_prompts_tell_the_model_to_infer_country_from_cities():
    from app.extraction.extractor import BATCH_SYSTEM_PROMPT, SYSTEM_PROMPT

    for prompt in (SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT):
        assert "Osaka -> JP" in prompt and "quoted or forwarded" in prompt
        assert "SEO" in prompt
