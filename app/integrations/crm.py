import functools
import logging
from typing import Protocol

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

HUBSPOT_API = "https://api.hubapi.com"
DEAL_TO_CONTACT = 3  # HubSpot-defined association type id: deal -> contact


def parse_owner_ids(raw: str) -> dict[str, str]:
    """Parse 'alice=123,bob=456' into {'alice': '123', 'bob': '456'}."""
    pairs = (item.split("=", 1) for item in raw.split(",") if "=" in item)
    return {rep.strip(): owner.strip() for rep, owner in pairs if rep.strip() and owner.strip()}


class CRMUnavailable(Exception):
    """Transient CRM failure (429, 5xx or network). The worker retries the task."""


class CRMClient(Protocol):
    def upsert_contact(self, email: str, properties: dict, owner: str | None = None) -> str: ...
    def create_deal(self, contact_id: str, name: str, owner: str | None = None) -> str: ...
    def deal_url(self, deal_id: str) -> str | None: ...


class MockCRM:
    """In-memory CRM. Idempotent on email, like the real HubSpot client."""

    def __init__(self) -> None:
        self.contacts: dict[str, dict] = {}
        self.deals: list[dict] = []

    def upsert_contact(self, email: str, properties: dict, owner: str | None = None) -> str:
        key = email.lower()
        contact = self.contacts.setdefault(key, {"id": f"mock-{len(self.contacts) + 1}"})
        contact.update({k: v for k, v in properties.items() if v not in (None, "")})
        if owner:
            contact["owner"] = owner
        return contact["id"]

    def create_deal(self, contact_id: str, name: str, owner: str | None = None) -> str:
        deal = {
            "id": f"deal-{len(self.deals) + 1}",
            "contact": contact_id,
            "name": name,
            "owner": owner,
        }
        self.deals.append(deal)
        return deal["id"]

    def deal_url(self, deal_id: str) -> str | None:
        return f"mock://deals/{deal_id}"


class HubSpotCRM:
    """HubSpot CRM v3 client using a private app token.

    Contacts are matched on email (search, then create or update), so repeat
    inquiries update the same contact instead of duplicating it.
    """

    def __init__(
        self,
        token: str,
        portal_id: str = "",
        owners: dict[str, str] | None = None,
        default_owner: str = "",
        pipeline: str = "default",
        deal_stage: str = "appointmentscheduled",
        client: httpx.Client | None = None,
    ) -> None:
        self.portal_id = portal_id
        self.owners = owners or {}
        self.default_owner = default_owner
        self.pipeline = pipeline
        self.deal_stage = deal_stage
        self.http = client or httpx.Client(base_url=HUBSPOT_API, timeout=15)
        self.http.headers["Authorization"] = f"Bearer {token}"

    # -- helpers -------------------------------------------------------------

    def _request(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        try:
            resp = self.http.request(method, path, json=json)
        except httpx.TransportError as exc:
            raise CRMUnavailable(str(exc)) from exc
        if resp.status_code == 429 or resp.status_code >= 500:
            raise CRMUnavailable(f"HubSpot {resp.status_code}: {resp.text[:200]}")
        return resp

    @staticmethod
    def _check(resp: httpx.Response) -> httpx.Response:
        if resp.status_code >= 400:
            raise RuntimeError(f"HubSpot {resp.status_code}: {resp.text[:300]}")
        return resp

    def _owner_id(self, rep: str | None) -> str | None:
        if not rep:
            return None
        owner_id = self.owners.get(rep) or self.default_owner or None
        if owner_id is None:
            log.warning("no HubSpot owner id for rep %r; leaving owner unset", rep)
        return owner_id

    # -- API -----------------------------------------------------------------

    def find_contact(self, email: str) -> str | None:
        body = {
            "filterGroups": [
                {"filters": [{"propertyName": "email", "operator": "EQ", "value": email.lower()}]}
            ],
            "properties": ["email"],
            "limit": 1,
        }
        resp = self._check(self._request("POST", "/crm/v3/objects/contacts/search", body))
        results = resp.json().get("results", [])
        return results[0]["id"] if results else None

    def upsert_contact(self, email: str, properties: dict, owner: str | None = None) -> str:
        props = {k: v for k, v in properties.items() if v not in (None, "")}
        props["email"] = email.lower()
        owner_id = self._owner_id(owner)
        if owner_id:
            props["hubspot_owner_id"] = owner_id

        contact_id = self.find_contact(email)
        if contact_id is None:
            resp = self._request("POST", "/crm/v3/objects/contacts", {"properties": props})
            if resp.status_code != 409:  # 409: created meanwhile (search index lag)
                return self._check(resp).json()["id"]
            contact_id = self.find_contact(email)
            if contact_id is None:
                raise RuntimeError("HubSpot reported a duplicate contact but search found none")

        self._check(
            self._request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", {"properties": props})
        )
        return contact_id

    def create_deal(self, contact_id: str, name: str, owner: str | None = None) -> str:
        props = {"dealname": name, "pipeline": self.pipeline, "dealstage": self.deal_stage}
        owner_id = self._owner_id(owner)
        if owner_id:
            props["hubspot_owner_id"] = owner_id
        body = {
            "properties": props,
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": DEAL_TO_CONTACT,
                        }
                    ],
                }
            ],
        }
        return self._check(self._request("POST", "/crm/v3/objects/deals", body)).json()["id"]

    def deal_url(self, deal_id: str) -> str | None:
        if not self.portal_id:
            return None
        return f"https://app.hubspot.com/contacts/{self.portal_id}/record/0-3/{deal_id}"


_mock = MockCRM()


@functools.cache
def _hubspot() -> HubSpotCRM:
    s = get_settings()
    if not s.hubspot_token:
        raise RuntimeError("CRM_MODE=hubspot but HUBSPOT_TOKEN is empty")
    owners = parse_owner_ids(s.hubspot_owner_ids)
    return HubSpotCRM(
        s.hubspot_token,
        s.hubspot_portal_id,
        owners,
        default_owner=s.hubspot_default_owner_id,
        pipeline=s.hubspot_pipeline,
        deal_stage=s.hubspot_deal_stage,
    )


def get_crm() -> CRMClient:
    mode = get_settings().crm_mode
    if mode == "mock":
        return _mock
    if mode == "hubspot":
        return _hubspot()
    raise ValueError(f"unknown CRM_MODE '{mode}' (use 'hubspot' or 'mock')")
