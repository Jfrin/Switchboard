import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, LeadRecord, RoutingDecision
from app.db.session import get_db
from app.logging_config import JsonFormatter
from app.main import app


def _client():
    engine = create_engine(
        "sqlite+pysqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        t0 = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)
        azure, gem = "azure:gpt-4.1-mini", "gemini-3.1-flash-lite"
        smb = "territory:APAC+segment:smb+round_robin"
        ent = "territory:AMER+segment:enterprise+round_robin"
        leads = [
            ("1", "routed", azure, "bob", smb, 2),
            ("2", "routed", azure, "carol", ent, 4),
            ("3", "review", gem, "review", "fallback:no_territory", 6),
            ("4", "failed", None, None, None, 0),
        ]
        for lead_id, status, model, rep, rule, secs in leads:
            db.add(LeadRecord(id=lead_id, sender=f"{lead_id}@x.com", subject="", body="b",
                              status=status, llm_model=model, created_at=t0))
            if rep:
                db.add(RoutingDecision(lead_id=lead_id, rep=rep, rule=rule, confidence=0.9,
                                       created_at=t0 + timedelta(seconds=secs)))
        db.commit()

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_metrics_exposes_prometheus_counts():
    try:
        res = _client().get("/metrics")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    body = res.text
    assert 'switchboard_leads_total{status="routed"} 2' in body
    assert 'switchboard_leads_total{status="failed"} 1' in body
    assert 'switchboard_leads_by_rep_total{rep="bob"} 1' in body
    assert 'switchboard_routing_decisions_total{rule="fallback:no_territory"} 1' in body
    assert 'switchboard_llm_answers_total{model="azure:gpt-4.1-mini"} 2' in body
    assert 'switchboard_llm_answers_total{model="none"} 1' in body
    assert 'switchboard_processing_seconds{quantile="p50"} 4.000' in body
    assert body.endswith("\n")


def test_json_formatter_emits_one_object_with_extra_fields():
    record = logging.LogRecord(
        "app.workers.tasks", logging.INFO, "f.py", 1, "lead processed", (), None
    )
    record.lead_id = "abc"
    record.duration_ms = 1234
    out = json.loads(JsonFormatter().format(record))
    assert out["msg"] == "lead processed" and out["level"] == "INFO"
    assert out["lead_id"] == "abc" and out["duration_ms"] == 1234
    assert out["ts"].endswith("+00:00")


def test_json_formatter_drops_uvicorn_color_codes():
    record = logging.LogRecord("uvicorn.error", logging.INFO, "f.py", 1, "started", (), None)
    record.color_message = "\x1b[36mstarted\x1b[0m"
    assert "color_message" not in json.loads(JsonFormatter().format(record))
