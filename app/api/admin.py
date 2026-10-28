"""Profile editor: a small web page (GET /admin) and the JSON API behind it.

Off unless ADMIN_UI=true, because it can rewrite files in config/profiles. If ADMIN_TOKEN
is set, every API call must send it in the X-Admin-Token header (the page asks for it).
"""

import hmac
import re
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.config import get_settings
from app.enrichment import enrich
from app.extraction.extractor import LLMUnavailable, extract_lead_with_model
from app.profile import Profile, ProfileError, active_path, apply_env_overrides, use_profile
from app.routing.engine import route, with_derived

PROFILES_DIR = Path("config/profiles")
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
PAGE = Path(__file__).resolve().parent.parent / "static" / "admin.html"


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    s = get_settings()
    if not s.admin_ui:
        raise HTTPException(404, "not found")
    if s.admin_token and not hmac.compare_digest(x_admin_token or "", s.admin_token):
        raise HTTPException(401, "wrong or missing admin token")


router = APIRouter()
api = APIRouter(prefix="/admin/api", dependencies=[Depends(require_admin)])


def _path(name: str) -> Path:
    if not NAME.match(name):
        raise HTTPException(400, "profile names use a-z, 0-9, - and _ (max 40 characters)")
    return PROFILES_DIR / f"{name}.yaml"


def _compile(text: str) -> Profile:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(400, "the profile must be a YAML mapping")
    try:
        return Profile(apply_env_overrides(data), source="this profile")
    except (ProfileError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


def _summary(p: Profile) -> dict:
    return {
        "name": p.name,
        "categories": p.categories,
        "fields": {
            "intent": "choice",
            **{k: (v or {}).get("type", "string") for k, v in p.fields.items()},
        },
        "derived": list(p.derived),
        "teams": p.teams,
        "rules": [
            {
                "label": r.get("label") or f"rule:{i}",
                "when": r.get("when") or "always",
                "to": r["to"],
            }
            for i, r in enumerate(p.rules, 1)
        ],
        "fallback_queue": p.fallback_queue,
        "crm": p.crm,
        "slack": p.slack,
    }


class Draft(BaseModel):
    yaml: str


class TryIn(BaseModel):
    yaml: str
    sender: str = ""
    subject: str = ""
    body: str = ""
    facts: dict | None = None  # skip the AI and route these extracted values directly


@router.get("/admin", response_class=HTMLResponse)
def page() -> str:
    if not get_settings().admin_ui:
        raise HTTPException(404, "not found")
    return PAGE.read_text(encoding="utf-8")


@api.get("/profiles")
def list_profiles() -> dict:
    files = sorted(p.stem for p in PROFILES_DIR.glob("*.yaml"))
    return {"profiles": files, "active": Path(active_path()).stem}


@api.get("/profiles/{name}")
def read_profile(name: str) -> dict:
    path = _path(name)
    if not path.exists():
        raise HTTPException(404, "no such profile")
    return {"name": name, "yaml": path.read_text(encoding="utf-8")}


@api.post("/validate")
def validate(draft: Draft) -> dict:
    return {"ok": True, "summary": _summary(_compile(draft.yaml))}


@api.put("/profiles/{name}")
def save_profile(name: str, draft: Draft) -> dict:
    path = _path(name)
    profile = _compile(draft.yaml)  # never write a file that would not load
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(draft.yaml, encoding="utf-8")
    tmp.replace(path)
    active = Path(active_path()).stem == name
    return {"saved": name, "active": active, "summary": _summary(profile)}


@api.post("/active/{name}")
def make_active(name: str) -> dict:
    """Make this profile the one the API and worker use (stored in ACTIVE_PROFILE_FILE)."""
    path = _path(name)
    if not path.exists():
        raise HTTPException(404, "no such profile")
    _compile(path.read_text(encoding="utf-8"))  # never activate a file that would not load
    target = Path(get_settings().active_profile_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(name + "\n", encoding="utf-8")
    return {"active": name}


@api.post("/to-form")
def to_form(draft: Draft) -> dict:
    """The YAML as plain data, for the form editor (comments are not kept)."""
    try:
        data = yaml.safe_load(draft.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(400, "the profile must be a YAML mapping")
    return {"data": data}


class FormData(BaseModel):
    data: dict


@api.post("/from-form")
def from_form(form: FormData) -> dict:
    text = yaml.safe_dump(
        form.data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )
    return {"yaml": text}


@api.post("/try")
def try_it(req: TryIn) -> dict:
    """Run one message through the draft profile: extraction (or given facts) and routing."""
    profile = _compile(req.yaml)
    threshold = get_settings().confidence_threshold
    model = refused = None
    if req.facts is not None:
        try:
            lead = profile.model.model_validate(req.facts)
        except ValueError as exc:
            raise HTTPException(400, f"those values do not fit this profile: {exc}") from exc
        confidence = lead.confidence if "confidence" in req.facts else 1.0
    else:
        if not req.body.strip():
            raise HTTPException(400, "paste an email body, or give extracted values instead")
        sender = req.sender or "unknown@example.com"
        try:
            with use_profile(profile):
                lead, model = extract_lead_with_model(sender, req.subject, req.body)
        except LLMUnavailable as exc:
            raise HTTPException(503, f"no model could answer right now: {exc}") from exc
        confidence = lead.confidence
        refused = model == "refused:content_filter"
    facts = lead.model_dump()
    enrichment = enrich(lead.domain) if profile.enrich_fill else {}
    for field in profile.enrich_fill:
        if facts.get(field) in (None, ""):
            facts[field] = enrichment.get(field)
    decision = route(
        facts=facts,
        confidence=confidence,
        refused=bool(refused),
        profile=profile,
        threshold=threshold,
        pick_rep=lambda team, reps: reps[0],  # the real round-robin counter is not touched
    )
    full = with_derived(profile, {**facts, "confidence": confidence})
    return {
        "model": model,
        "extracted": lead.model_dump(),
        "after_enrichment": {k: v for k, v in facts.items() if v != lead.model_dump().get(k)},
        "derived": {k: full.get(k) for k in profile.derived},
        "decision": decision.to_dict(),
        "threshold": threshold,
        "note": "Rep shown is the first in the team; the live round-robin counter was not used.",
    }


router.include_router(api)
