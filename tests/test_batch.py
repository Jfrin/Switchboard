import json

from app.extraction.extractor import LLMResult, extract_leads_batch

EMAILS = [
    {"from": "a@acme.com", "subject": "s1", "body": "b1"},
    {"from": "b@zeta.io", "subject": "s2", "body": "b2"},
    {"from": "c@omega.dev", "subject": "s3", "body": "b3"},
]


def batch_of(items):
    return lambda emails: LLMResult(json.dumps(items), "m1")


def single(text="{}", model="m1"):
    calls = []

    def llm(sender, subject, body):
        calls.append(sender)
        return LLMResult(json.dumps({"company": "Alone", "confidence": 0.5}), model)

    return llm, calls


def test_one_request_returns_all_leads_matched_by_id():
    items = [
        {"id": "2", "company": "Omega", "intent": "demo", "confidence": 0.9},
        {"id": "0", "company": "Acme", "intent": "pricing", "confidence": 0.9},
        {"id": "1", "company": "Zeta", "intent": "support", "confidence": 0.8},
    ]
    llm, calls = single()
    out = extract_leads_batch(EMAILS, llm_batch=batch_of(items), llm=llm)
    assert [lead.company for lead, _ in out] == ["Acme", "Zeta", "Omega"]
    assert all(model == "m1" for _, model in out) and calls == []
    assert out[0][0].domain == "acme.com"  # regex fill-in still applied


def test_missing_item_is_redone_alone():
    items = [{"id": "0", "company": "Acme", "confidence": 0.9}]
    llm, calls = single()
    out = extract_leads_batch(EMAILS, llm_batch=batch_of(items), llm=llm)
    assert out[0][0].company == "Acme"
    assert [lead.company for lead, _ in out[1:]] == ["Alone", "Alone"]
    assert calls == ["b@zeta.io", "c@omega.dev"]


def test_invalid_and_duplicate_ids_are_ignored():
    items = [
        {"id": "0", "company": "Acme", "confidence": 0.9},
        {"id": "0", "company": "Imposter", "confidence": 0.9},
        {"id": "7", "company": "Ghost", "confidence": 0.9},
        {"id": "1", "intent": "not-an-intent"},
    ]
    llm, calls = single()
    out = extract_leads_batch(EMAILS, llm_batch=batch_of(items), llm=llm)
    assert out[0][0].company == "Acme"
    assert calls == ["b@zeta.io", "c@omega.dev"]


def test_garbage_batch_falls_back_to_individual_calls():
    llm, calls = single()
    out = extract_leads_batch(
        EMAILS, llm_batch=lambda e: LLMResult("not json", "m1"), llm=llm
    )
    assert len(out) == 3 and len(calls) == 3


def test_auto_batch_follows_first_model(monkeypatch):
    from app.config import get_settings
    from app.extraction.extractor import default_batch_size

    monkeypatch.setenv("GEMINI_BATCH_SIZE", "30")
    monkeypatch.setenv("AZURE_BATCH_SIZE", "10")
    get_settings.cache_clear()
    assert default_batch_size(["gemini-3.5-flash-lite", "azure:gpt-4.1-mini"]) == 30
    assert default_batch_size(["azure:gpt-4.1-mini", "gemini-3.5-flash-lite"]) == 10
    assert default_batch_size([]) == 30
    get_settings.cache_clear()


def test_refused_batch_is_redone_one_by_one():
    from app.extraction.extractor import LLMRefused

    def refuse(emails):
        raise LLMRefused("filtered")

    llm, calls = single()
    out = extract_leads_batch(EMAILS, llm_batch=refuse, llm=llm)
    assert len(out) == 3 and len(calls) == 3
