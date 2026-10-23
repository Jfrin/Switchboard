import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import EnrichmentCache
from app.enrichment.base import FREE_DOMAINS, EnrichmentProvider
from app.enrichment.mock import MockProvider

log = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=30)


def get_provider() -> EnrichmentProvider:
    name = get_settings().enrichment_provider
    if name == "mock":
        return MockProvider()
    raise NotImplementedError(f"enrichment provider '{name}' not implemented yet")


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def enrich(domain: str | None, db: Session | None = None) -> dict:
    """Best-effort company lookup by domain; never raises.

    With a session, results are cached per domain for 30 days so repeat senders
    from the same company don't spend provider quota. Failed or empty lookups
    are not cached, so they are retried next time.
    """
    if not domain or domain in FREE_DOMAINS:
        return {}

    if db is not None:
        try:
            row = db.get(EnrichmentCache, domain)
            if row is not None and datetime.now(UTC) - _aware(row.created_at) < CACHE_TTL:
                return row.data
        except Exception:
            log.warning("enrichment cache read failed for %s", domain, exc_info=True)

    try:
        data = get_provider().lookup(domain)
    except Exception:
        log.warning("enrichment lookup failed for %s", domain, exc_info=True)
        return {}

    if db is not None and data:
        try:
            with db.begin_nested():
                db.merge(
                    EnrichmentCache(domain=domain, data=data, created_at=datetime.now(UTC))
                )
        except Exception:
            log.warning("enrichment cache write failed for %s", domain, exc_info=True)
    return data
