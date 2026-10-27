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
    from app.profile import get_profile

    profile = get_profile()
    for prompt in (profile.system_prompt, profile.batch_prompt):
        assert "Osaka -> JP" in prompt and "quoted or forwarded" in prompt
        assert "SEO" in prompt


def test_null_choice_falls_back_to_its_default():
    payload = json.dumps({"intent": None, "urgency": None, "confidence": 0.9})
    lead = extract_lead("jane@acme.com", "s", "b", llm=lambda *a: payload)
    assert lead.intent == "other" and lead.urgency == "medium"
