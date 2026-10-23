class MockProvider:
    """Deterministic fake data so the project runs without API keys."""

    _KNOWN = {
        "acme.com": {"company": "Acme Logistics", "employee_count": 220, "country": "SG"},
        "bigcorp.com": {"company": "BigCorp", "employee_count": 5000, "country": "US"},
    }

    def lookup(self, domain: str) -> dict:
        return self._KNOWN.get(domain, {"company": domain.split(".")[0].title()})
