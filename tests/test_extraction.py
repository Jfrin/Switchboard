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
