import shutil

import pytest
from fastapi.testclient import TestClient

from app.api import admin
from app.config import get_settings
from app.main import app
from app.profile import get_profile

SALES = open("config/profiles/sales.yaml", encoding="utf-8").read()


@pytest.fixture
def client(tmp_path, monkeypatch):
    shutil.copytree("config/profiles", tmp_path / "profiles")
    monkeypatch.setattr(admin, "PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setenv("ADMIN_UI", "true")
    monkeypatch.setenv("ADMIN_TOKEN", "")
    monkeypatch.setenv("LLM_MODELS", "")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()
    get_profile.cache_clear()


def test_off_by_default(monkeypatch):
    monkeypatch.setenv("ADMIN_UI", "false")
    get_settings.cache_clear()
    try:
        c = TestClient(app)
        assert c.get("/admin").status_code == 404
        assert c.get("/admin/api/profiles").status_code == 404
    finally:
        get_settings.cache_clear()


def test_page_and_list(client):
    assert "Switchboard profiles" in client.get("/admin").text
    out = client.get("/admin/api/profiles").json()
    assert {"sales", "support"} <= set(out["profiles"])


def test_token_is_required_when_set(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    get_settings.cache_clear()
    assert client.get("/admin/api/profiles").status_code == 401
    ok = client.get("/admin/api/profiles", headers={"X-Admin-Token": "s3cret"})
    assert ok.status_code == 200


def test_validate_reports_the_problem(client):
    bad = SALES.replace("to: {team: \"{segment}\"}", "to: {team: ghost}")
    r = client.post("/admin/api/validate", json={"yaml": bad})
    assert r.status_code == 400 and "ghost" in r.json()["detail"]
    r = client.post("/admin/api/validate", json={"yaml": "name: [unclosed"})
    assert r.status_code == 400 and "YAML" in r.json()["detail"]
    ok = client.post("/admin/api/validate", json={"yaml": SALES}).json()
    assert ok["ok"] and ok["summary"]["name"] == "sales"


def test_save_writes_only_valid_files(client):
    changed = SALES.replace("alice, bob", "zed, yara")
    r = client.put("/admin/api/profiles/sales", json={"yaml": changed})
    assert r.status_code == 200 and r.json()["summary"]["teams"]["smb"] == ["zed", "yara"]
    assert "zed, yara" in client.get("/admin/api/profiles/sales").json()["yaml"]
    r = client.put("/admin/api/profiles/sales", json={"yaml": "name: x"})
    assert r.status_code == 400
    assert "zed, yara" in client.get("/admin/api/profiles/sales").json()["yaml"]  # untouched


def test_new_profile_names_are_restricted(client):
    for name in ("..%2Fx", "Bad Name", "a" * 50):
        assert client.put(f"/admin/api/profiles/{name}", json={"yaml": SALES}).status_code in (
            400, 404, 405)
    assert client.put("/admin/api/profiles/copy-1", json={"yaml": SALES}).status_code == 200


def test_try_with_given_values_routes_without_the_ai(client):
    facts = {"intent": "pricing", "country": "SG", "employee_count": 600, "confidence": 0.9}
    r = client.post("/admin/api/try", json={"yaml": SALES, "facts": facts}).json()
    assert r["decision"]["team"] == "enterprise" and r["decision"]["rep"] == "carol"
    assert r["derived"] == {"region": "APAC", "segment": "enterprise"}


def test_try_with_bad_values_explains(client):
    r = client.post("/admin/api/try", json={"yaml": SALES, "facts": {"urgency": "whenever"}})
    assert r.status_code == 400 and "do not fit" in r.json()["detail"]


def test_try_with_a_message_uses_the_draft_profile(client, monkeypatch):
    support = open("config/profiles/support.yaml", encoding="utf-8").read()
    seen = {}

    def fake(sender, subject, body, llm=None):
        model = get_profile().model  # must be the draft's model, not the active profile's
        seen["fields"] = set(model.model_fields)
        return model(intent="outage", severity="high", confidence=0.9), "stub"

    monkeypatch.setattr(admin, "extract_lead_with_model", fake)
    r = client.post("/admin/api/try", json={"yaml": support, "body": "site is down"}).json()
    assert "severity" in seen["fields"] and "urgency" not in seen["fields"]
    assert r["decision"]["team"] == "oncall" and r["model"] == "stub"
