"""Repeat senders keep their rep; failed leads can be put back on the queue."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import routes
from app.db.models import Base, LeadRecord
from app.db.session import get_db
from app.main import app
from app.workers import tasks
from app.workers.tasks import sticky_picker


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _lead(db, id, sender, status, rep=None, minutes_ago=0):
    db.add(LeadRecord(
        id=id, sender=sender, subject="s", body="b", status=status,
        decision={"rep": rep} if rep else None,
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    ))
    db.commit()


def _base():
    calls = []

    def base(team, reps):
        calls.append(team)
        return reps[0]

    return base, calls


def test_repeat_sender_keeps_their_rep(engine):
    with Session(engine) as db:
        _lead(db, "old", "Jane@Acme.com", "routed", rep="bob", minutes_ago=5)
        base, calls = _base()
        pick = sticky_picker(db, "jane@acme.com", "new", base)
        assert pick("smb", ["alice", "bob"]) == "bob"  # case-insensitive match
        assert calls == []  # the round-robin counter did not move


def test_new_sender_uses_round_robin(engine):
    with Session(engine) as db:
        _lead(db, "old", "someone@else.com", "routed", rep="bob")
        base, calls = _base()
        assert sticky_picker(db, "new@acme.com", "x", base)("smb", ["alice", "bob"]) == "alice"
        assert calls == ["smb"]


def test_rep_not_in_the_team_falls_back_to_round_robin(engine):
    with Session(engine) as db:
        _lead(db, "old", "jane@acme.com", "routed", rep="carol")
        base, _ = _base()
        assert sticky_picker(db, "jane@acme.com", "x", base)("smb", ["alice", "bob"]) == "alice"


def test_only_routed_leads_count_and_the_latest_wins(engine):
    with Session(engine) as db:
        _lead(db, "a", "jane@acme.com", "routed", rep="alice", minutes_ago=30)
        _lead(db, "b", "jane@acme.com", "routed", rep="bob", minutes_ago=10)
        _lead(db, "c", "jane@acme.com", "review", rep=None, minutes_ago=1)
        _lead(db, "d", "jane@acme.com", "failed", rep="alice", minutes_ago=0)
        base, _ = _base()
        assert sticky_picker(db, "jane@acme.com", "z", base)("smb", ["alice", "bob"]) == "bob"


def test_pipeline_uses_sticky_only_when_the_profile_allows(engine, monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(tasks, "notify", lambda *_: None)
    from app.profile import get_profile

    model = get_profile().model
    monkeypatch.setattr(
        tasks, "extract_lead_with_model",
        lambda *_: (model(email="jane@zeta.io", domain="zeta.io", company="Zeta",
                          intent="pricing", country="SG", employee_count=10,
                          confidence=0.9), "stub"),
    )
    with Session(engine) as db:
        _lead(db, "old", "jane@zeta.io", "routed", rep="bob", minutes_ago=5)
        _lead(db, "new", "jane@zeta.io", "queued")
    tasks.run_pipeline("new")
    with Session(engine) as db:
        assert db.get(LeadRecord, "new").decision["rep"] == "bob"  # alice is first in line


def test_failed_lead_can_be_retried(engine, monkeypatch):
    queued = []
    from app.workers import tasks as t

    monkeypatch.setattr(t.process_lead, "delay", queued.append)
    with Session(engine) as db:
        _lead(db, "f1", "a@x.com", "failed")
        _lead(db, "f2", "b@x.com", "failed")
        _lead(db, "ok", "c@x.com", "routed", rep="alice")

    def db_override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        c = TestClient(app)
        assert c.post("/leads/ok/retry").status_code == 409
        assert c.post("/leads/missing/retry").status_code == 404
        r = c.post("/leads/f1/retry")
        assert r.status_code == 200 and r.json()["status"] == "queued"
        assert queued == ["f1"]
        out = c.post("/leads/retry-failed").json()
        assert out["requeued"] == ["f2"]  # f1 is already queued again
        assert queued == ["f1", "f2"]
    finally:
        app.dependency_overrides.clear()


def test_routes_module_has_the_retry_endpoints():
    paths = {r.path for r in routes.router.routes}
    assert {"/leads/{lead_id}/retry", "/leads/retry-failed"} <= paths
