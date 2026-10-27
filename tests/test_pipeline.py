"""run_pipeline end to end for both profiles (in-memory DB, stubbed extraction and Slack)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base, LeadRecord, RoutingDecision
from app.profile import get_profile
from app.workers import tasks


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    sent = []
    monkeypatch.setattr(tasks, "notify", sent.append)
    yield engine, sent
    get_settings().profile_path = "config/profiles/sales.yaml"
    get_profile.cache_clear()


def _run(engine, monkeypatch, profile, sender, fields):
    s = get_settings()
    s.profile_path = f"config/profiles/{profile}.yaml"
    get_profile.cache_clear()
    model = get_profile().model
    monkeypatch.setattr(
        tasks, "extract_lead_with_model",
        lambda *_: (model(email=sender, domain=sender.split("@")[1], **fields), "stub"),
    )
    with Session(engine) as db:
        db.add(LeadRecord(id="1", sender=sender, subject="s", body="b"))
        db.commit()
    tasks.run_pipeline("1")
    with Session(engine) as db:
        return db.get(LeadRecord, "1"), db.query(RoutingDecision).all()


def test_sales_lead_is_routed_with_crm_and_slack(env, monkeypatch):
    engine, sent = env
    rec, audit = _run(engine, monkeypatch, "sales", "jane@zeta.io", {
        "company": "Zeta", "intent": "pricing", "country": "SG", "employee_count": 20,
        "confidence": 0.9, "name": "Jane Roe",
    })
    assert rec.status == "routed" and rec.decision["rep"] == "alice"
    assert rec.decision["deal_id"]  # mock CRM created a deal
    assert audit[0].rule == "territory:APAC+segment:smb+round_robin"
    assert sent[0].startswith("New lead: Zeta") and "assigned=alice" in sent[0]


def test_sales_enrichment_fills_missing_fields(env, monkeypatch):
    engine, _ = env
    rec, _ = _run(engine, monkeypatch, "sales", "bob@acme.com", {
        "company": "Acme", "intent": "demo", "confidence": 0.9,
    })
    assert rec.status == "routed"  # country and size came from the mock lookup


def test_support_ticket_skips_crm_and_uses_its_own_teams(env, monkeypatch):
    engine, sent = env
    rec, audit = _run(engine, monkeypatch, "support", "sam@northwind.example", {
        "intent": "outage", "summary": "Dashboard returns 503", "severity": "high",
        "confidence": 0.9,
    })
    assert rec.status == "routed" and rec.decision["team"] == "oncall"
    assert rec.decision["deal_id"] is None  # crm is off in this profile
    assert audit[0].rule == "outage->oncall"
    assert sent[0].startswith("New ticket: Dashboard returns 503")
    assert "severity=high" in sent[0]


def test_support_queue_target_is_reported_as_review(env, monkeypatch):
    engine, sent = env
    rec, _ = _run(engine, monkeypatch, "support", "olu@nimbus.example", {
        "intent": "feature_request", "summary": "Dark mode", "confidence": 0.9,
    })
    assert rec.status == "review" and rec.decision["team"] == "product-feedback"
    assert "assigned=product-feedback" in sent[0]
