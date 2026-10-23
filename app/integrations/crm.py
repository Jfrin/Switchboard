from typing import Protocol

from app.config import get_settings


class CRMClient(Protocol):
    def upsert_contact(self, email: str, properties: dict) -> str: ...
    def create_deal(self, contact_id: str, name: str, owner: str | None) -> str: ...


class MockCRM:
    """In-memory CRM. Idempotent on email, like the real HubSpot client must be."""

    def __init__(self) -> None:
        self.contacts: dict[str, dict] = {}
        self.deals: list[dict] = []

    def upsert_contact(self, email: str, properties: dict) -> str:
        key = email.lower()
        contact = self.contacts.setdefault(key, {"id": f"mock-{len(self.contacts) + 1}"})
        contact.update(properties)
        return contact["id"]

    def create_deal(self, contact_id: str, name: str, owner: str | None) -> str:
        deal = {"id": f"deal-{len(self.deals) + 1}", "contact": contact_id, "name": name,
                "owner": owner}
        self.deals.append(deal)
        return deal["id"]


_mock = MockCRM()


def get_crm() -> CRMClient:
    mode = get_settings().crm_mode
    if mode == "mock":
        return _mock
    raise NotImplementedError("HubSpot client not implemented yet (plan.md Phase 3)")
