from app.config import get_settings
from app.enrichment.base import FREE_DOMAINS, EnrichmentProvider
from app.enrichment.mock import MockProvider


def get_provider() -> EnrichmentProvider:
    name = get_settings().enrichment_provider
    if name == "mock":
        return MockProvider()
    raise NotImplementedError(f"enrichment provider '{name}' not implemented yet")


def enrich(domain: str | None) -> dict:
    """Never raises: enrichment is best-effort."""
    if not domain or domain in FREE_DOMAINS:
        return {}
    try:
        return get_provider().lookup(domain)
    except Exception:
        return {}
