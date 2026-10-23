import json

import httpx
import pytest

from app.integrations.crm import CRMUnavailable, HubSpotCRM, MockCRM

OWNERS = {"alice": "555"}


def make_crm(responses, **kwargs):
    """HubSpotCRM whose HTTP calls are answered from `responses`, in order."""
    calls: list[httpx.Request] = []
    queue = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status, body = next(queue)
        return httpx.Response(status, json=body)

    client = httpx.Client(
        base_url="https://api.hubapi.com", transport=httpx.MockTransport(handler)
    )
    return HubSpotCRM("tok", client=client, **kwargs), calls


def body_of(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_creates_contact_when_not_found():
    crm, calls = make_crm([(200, {"results": []}), (201, {"id": "101"})], owners=OWNERS)
    contact_id = crm.upsert_contact(
        "Jane@Acme.com", {"company": "Acme", "phone": None, "jobtitle": ""}, owner="alice"
    )
    assert contact_id == "101"
    search, create = calls
    assert search.url.path == "/crm/v3/objects/contacts/search"
    assert body_of(search)["filterGroups"][0]["filters"][0]["value"] == "jane@acme.com"
    assert create.method == "POST"
    assert body_of(create)["properties"] == {
        "company": "Acme",
        "email": "jane@acme.com",
        "hubspot_owner_id": "555",
    }
    assert create.headers["authorization"] == "Bearer tok"


def test_updates_existing_contact():
    crm, calls = make_crm([(200, {"results": [{"id": "7"}]}), (200, {"id": "7"})])
    assert crm.upsert_contact("jane@acme.com", {"company": "Acme"}) == "7"
    assert calls[1].method == "PATCH"
    assert calls[1].url.path == "/crm/v3/objects/contacts/7"


def test_duplicate_conflict_falls_back_to_update():
    crm, calls = make_crm(
        [
            (200, {"results": []}),  # search lag: contact not visible yet
            (409, {"message": "Contact already exists"}),
            (200, {"results": [{"id": "9"}]}),
            (200, {"id": "9"}),
        ]
    )
    assert crm.upsert_contact("jane@acme.com", {}) == "9"
    assert [c.method for c in calls] == ["POST", "POST", "POST", "PATCH"]


def test_deal_is_associated_with_contact_and_owner():
    crm, calls = make_crm([(201, {"id": "d1"})], owners=OWNERS)
    assert crm.create_deal("101", "Acme inquiry", owner="alice") == "d1"
    body = body_of(calls[0])
    assert calls[0].url.path == "/crm/v3/objects/deals"
    assert body["properties"] == {
        "dealname": "Acme inquiry",
        "pipeline": "default",
        "dealstage": "appointmentscheduled",
        "hubspot_owner_id": "555",
    }
    assoc = body["associations"][0]
    assert assoc["to"] == {"id": "101"}
    assert assoc["types"][0]["associationTypeId"] == 3


def test_unknown_rep_leaves_owner_unset():
    crm, calls = make_crm([(201, {"id": "d1"})], owners={})
    crm.create_deal("101", "x", owner="bob")
    assert "hubspot_owner_id" not in body_of(calls[0])["properties"]


def test_rate_limit_is_retryable():
    crm, _ = make_crm([(429, {"message": "slow down"})])
    with pytest.raises(CRMUnavailable):
        crm.upsert_contact("jane@acme.com", {})


def test_client_error_is_not_retryable():
    crm, _ = make_crm([(400, {"message": "bad request"})])
    with pytest.raises(RuntimeError):
        crm.upsert_contact("jane@acme.com", {})


def test_deal_url_needs_portal_id():
    with_portal, _ = make_crm([], portal_id="123")
    without_portal, _ = make_crm([])
    assert with_portal.deal_url("d1") == "https://app.hubspot.com/contacts/123/record/0-3/d1"
    assert without_portal.deal_url("d1") is None


def test_mock_crm_is_idempotent_on_email():
    crm = MockCRM()
    first = crm.upsert_contact("Jane@Acme.com", {"company": "Acme"}, owner="alice")
    second = crm.upsert_contact("jane@acme.com", {"company": "Acme Inc", "phone": None})
    assert first == second
    assert len(crm.contacts) == 1
    assert crm.contacts["jane@acme.com"]["company"] == "Acme Inc"
    deal_id = crm.create_deal(first, "Acme inquiry", owner="alice")
    assert crm.deals[0]["contact"] == first
    assert crm.deal_url(deal_id) == f"mock://deals/{deal_id}"
