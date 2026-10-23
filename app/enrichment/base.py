from typing import Protocol

FREE_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
}


class EnrichmentProvider(Protocol):
    def lookup(self, domain: str) -> dict:
        """Return e.g. {'company': str, 'employee_count': int, 'country': 'SG'}."""
        ...
