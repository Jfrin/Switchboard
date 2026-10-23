from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import enrichment
from app.db.models import Base, EnrichmentCache, RoundRobinState
from app.routing.round_robin import make_db_picker


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class CountingProvider:
    def __init__(self, data=None, fail=False):
        self.calls = 0
        self.data = data if data is not None else {"company": "Acme", "employee_count": 220}
        self.fail = fail

    def lookup(self, domain):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return self.data


def use(monkeypatch, provider):
    monkeypatch.setattr(enrichment, "get_provider", lambda: provider)


def test_second_lookup_is_served_from_cache(db, monkeypatch):
    provider = CountingProvider()
    use(monkeypatch, provider)
    first = enrichment.enrich("acme.com", db)
    db.commit()
    second = enrichment.enrich("acme.com", db)
    assert first == second == provider.data
    assert provider.calls == 1


def test_expired_cache_entry_is_refreshed(db, monkeypatch):
    provider = CountingProvider({"company": "Fresh"})
    use(monkeypatch, provider)
    old = datetime.now(UTC) - timedelta(days=31)
    db.add(EnrichmentCache(domain="acme.com", data={"company": "Stale"}, created_at=old))
    db.commit()
    assert enrichment.enrich("acme.com", db) == {"company": "Fresh"}
    assert provider.calls == 1


def test_failures_and_empty_results_are_not_cached(db, monkeypatch):
    use(monkeypatch, CountingProvider(fail=True))
    assert enrichment.enrich("acme.com", db) == {}
    use(monkeypatch, CountingProvider(data={}))
    assert enrichment.enrich("acme.com", db) == {}
    db.commit()
    assert db.get(EnrichmentCache, "acme.com") is None


def test_free_email_domains_skip_the_provider(db, monkeypatch):
    provider = CountingProvider()
    use(monkeypatch, provider)
    assert enrichment.enrich("gmail.com", db) == {}
    assert enrichment.enrich(None, db) == {}
    assert provider.calls == 0


def test_round_robin_cycles_and_persists_state(db):
    pick = make_db_picker(db)
    reps = ["alice", "bob"]
    assert [pick("smb", reps) for _ in range(3)] == ["alice", "bob", "alice"]
    db.commit()
    assert db.get(RoundRobinState, "smb").counter == 3


def test_round_robin_recovers_when_another_worker_inserts_first(tmp_path, monkeypatch):
    """Two real sessions: the other worker commits the team's first row after our
    SELECT saw nothing, so our INSERT hits the primary key and must recover."""
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'rr.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as other, Session(engine) as ours:
        other.add(RoundRobinState(team="smb", counter=5))
        other.commit()

        real_scalar = ours.scalar
        stale = {"first": True}

        def scalar(stmt, *args, **kwargs):
            if stale["first"]:  # our first SELECT ran before the other worker committed
                stale["first"] = False
                return None
            return real_scalar(stmt, *args, **kwargs)

        monkeypatch.setattr(ours, "scalar", scalar)
        assert make_db_picker(ours)("smb", ["alice", "bob"]) == "bob"  # counter 5 -> index 1
        ours.commit()

    with Session(engine) as check:
        assert check.get(RoundRobinState, "smb").counter == 6
