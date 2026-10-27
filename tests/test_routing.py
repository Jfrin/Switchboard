from itertools import count

import pytest

from app.config import get_settings
from app.profile import ProfileError, load_profile
from app.routing.engine import route, with_derived

PROFILE = load_profile("config/profiles/sales.yaml")


def _picker():
    n = count()
    return lambda team, reps: reps[next(n) % len(reps)]


def _route(profile=PROFILE, confidence=0.9, **facts):
    base = {"country": "SG", "employee_count": 200, "intent": "pricing"}
    return route(
        facts={**base, **facts},
        confidence=confidence,
        profile=profile,
        threshold=0.7,
        pick_rep=_picker(),
    )


def test_smb_in_territory():
    d = _route()
    assert d.team == "smb" and d.rep == "alice"
    assert d.rule == "territory:APAC+segment:smb+round_robin"


def test_enterprise_segment():
    d = _route(employee_count=5000, country="US")
    assert d.team == "enterprise" and d.rep == "carol"


def test_round_robin_cycles():
    pick = _picker()
    reps = [
        route(facts={"country": "SG", "employee_count": 10, "intent": "demo"}, confidence=0.9,
              profile=PROFILE, threshold=0.7, pick_rep=pick).rep
        for _ in range(3)
    ]
    assert reps == ["alice", "bob", "alice"]


def test_low_confidence_goes_to_review():
    d = _route(confidence=0.3)
    assert d.rep is None and d.rule == "fallback:low_confidence"


def test_unknown_territory_goes_to_review():
    d = _route(country="ZZ")
    assert d.rep is None and d.rule == "fallback:no_territory"


def test_missing_size_goes_to_review():
    d = _route(employee_count=None)
    assert d.rep is None and d.rule == "fallback:no_segment"


def test_spam_and_other_never_reach_a_rep():
    for intent in ("spam", "other"):
        d = _route(intent=intent, confidence=0.99)
        assert d.team == "review" and d.rep is None
        assert d.rule == f"fallback:intent_{intent}"


def test_real_intents_still_route():
    assert _route(intent="pricing").rep == "alice"
    assert _route(intent="support").rep == "alice"


def test_refused_message_goes_to_review_with_its_own_rule():
    d = route(facts={}, confidence=0.0, profile=PROFILE, threshold=0.7,
              pick_rep=_picker(), refused=True)
    assert d.team == "review" and d.rep is None
    assert d.rule == "fallback:content_filtered"


def test_country_match_ignores_case():
    assert _route(country="sg").rule == "territory:APAC+segment:smb+round_robin"


def test_derived_fields():
    out = with_derived(PROFILE, {"country": "DE", "employee_count": 500})
    assert out["region"] == "EMEA" and out["segment"] == "enterprise"
    out = with_derived(PROFILE, {"country": None, "employee_count": None})
    assert out["region"] is None and out["segment"] is None


# ---- env overrides ------------------------------------------------------------------

def test_env_overrides_replace_yaml_values(monkeypatch):
    monkeypatch.setenv("ROUTING_SMB_REPS", "smb-apac-1, smb-apac-2")
    monkeypatch.setenv("ROUTING_ENTERPRISE_REPS", "ent-global-1")
    monkeypatch.setenv("ROUTING_ENTERPRISE_MIN_EMPLOYEES", "1000")
    monkeypatch.setenv("ROUTING_TERRITORIES", "ASEAN=sg,id;ROW=US,GB")
    monkeypatch.setenv("ROUTING_FALLBACK_QUEUE", "human-review")
    get_settings.cache_clear()
    try:
        p = load_profile("config/profiles/sales.yaml")
        assert p.teams["smb"] == ["smb-apac-1", "smb-apac-2"]
        assert p.teams["enterprise"] == ["ent-global-1"]
        d = _route(p, country="ID", employee_count=700)
        assert d.team == "smb" and d.rep == "smb-apac-1"
        assert d.rule == "territory:ASEAN+segment:smb+round_robin"
        d = _route(p, country="DE", employee_count=700)
        assert d.team == "human-review" and d.rule == "fallback:no_territory"

        monkeypatch.setenv("ROUTING_TERRITORIES", "APAC SG PH")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="REGION=CC"):
            load_profile("config/profiles/sales.yaml")
        monkeypatch.setenv("ROUTING_TERRITORIES", "")
        monkeypatch.setenv("ROUTING_ENTERPRISE_MIN_EMPLOYEES", "lots")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="whole number"):
            load_profile("config/profiles/sales.yaml")
    finally:
        get_settings.cache_clear()


def test_any_team_can_be_set_from_env(monkeypatch):
    monkeypatch.setenv("ROUTING_TEAM_BILLING_REPS", "zed, yara")
    get_settings.cache_clear()
    try:
        p = load_profile("config/profiles/support.yaml")
        assert p.teams["billing"] == ["zed", "yara"]
    finally:
        get_settings.cache_clear()


def test_without_env_the_yaml_defaults_are_used():
    assert PROFILE.teams["smb"] == ["alice", "bob"]
    assert PROFILE.teams["enterprise"] == ["carol", "dave"]


# ---- support profile ----------------------------------------------------------------

SUPPORT = load_profile("config/profiles/support.yaml")


def _support(confidence=0.9, **facts):
    return route(facts=facts, confidence=confidence, profile=SUPPORT, threshold=0.7,
                 pick_rep=lambda team, reps: reps[0])


def test_support_outage_pages_oncall():
    d = _support(intent="outage", severity="low")
    assert d.team == "oncall" and d.rep == "erin" and d.rule == "outage->oncall"


def test_support_rules_run_in_order():
    assert _support(intent="bug", severity="high", plan="enterprise").team == "oncall"
    assert _support(intent="bug", severity="medium", plan="enterprise").team == "engineering"
    assert _support(intent="bug", severity="medium", plan="free").team == "support"


def test_support_templated_label_and_queue_target():
    assert _support(intent="how_to").rule == "how_to->support"
    d = _support(intent="feature_request")
    assert d.team == "product-feedback" and d.rep is None


def test_support_fallback_queue_is_its_own():
    d = _support(intent="spam")
    assert d.team == "triage" and d.rule == "fallback:intent_spam"


# ---- engine edge cases --------------------------------------------------------------

def _tiny(rules, **extra):
    data = {
        "name": "t", "categories": ["a", "b"],
        "fields": {"amount": {"type": "integer"}, "tag": {"type": "string"}},
        "teams": {"x": {"reps": ["r1", "r2"]}},
        "rules": rules, **extra,
    }
    from app.profile import Profile
    return Profile(data)


def _go(profile, **facts):
    return route(facts=facts, confidence=1.0, profile=profile, threshold=0.5,
                 pick_rep=lambda team, reps: reps[0])


def test_comparison_operators():
    p = _tiny([
        {"when": {"amount": {"gte": 100, "lt": 1000}}, "to": {"team": "x"}, "label": "mid"},
        {"to": {"queue": "other"}, "label": "rest"},
    ])
    assert _go(p, amount=100).rule == "mid"
    assert _go(p, amount=999).rule == "mid"
    assert _go(p, amount=1000).rule == "rest"
    assert _go(p, amount=None).rule == "rest"


def test_contains_and_not_in():
    p = _tiny([
        {"when": {"tag": {"contains": "vip"}}, "to": {"team": "x"}, "label": "vip"},
        {"when": {"intent": {"not_in": ["a"]}}, "to": {"queue": "bq"}, "label": "not-a"},
        {"to": {"queue": "fallback"}, "label": "rest"},
    ])
    assert _go(p, tag="Big VIP client", intent="a").rule == "vip"
    assert _go(p, tag=None, intent="b").rule == "not-a"
    assert _go(p, tag=None, intent="a").team == "review"


def test_no_matching_rule_goes_to_fallback():
    p = _tiny([{"when": {"intent": "a"}, "to": {"team": "x"}, "label": "only-a"}])
    d = _go(p, intent="b")
    assert d.team == "review" and d.rule == "fallback:no_match"


def test_unknown_templated_team_goes_to_fallback():
    p = _tiny([{"to": {"team": "{tag}"}}])
    d = _go(p, tag="ghosts")
    assert d.team == "review" and d.rule == "fallback:unknown_team:ghosts"


def test_unlabeled_rule_gets_its_number():
    p = _tiny([{"to": {"team": "x"}}])
    assert _go(p).rule == "rule:1"


# ---- validation ---------------------------------------------------------------------

def _bad(match, **changes):
    data = {
        "name": "t", "categories": ["a", "b"], "fields": {"tag": {"type": "string"}},
        "teams": {"x": {"reps": ["r"]}}, "rules": [{"to": {"team": "x"}}],
    }
    data.update(changes)
    from app.profile import Profile
    with pytest.raises(ProfileError, match=match):
        Profile(data)


def test_validation_messages_name_the_problem():
    _bad("at least two", categories=["a"])
    _bad("default_category", default_category="zzz")
    _bad("unknown field 'nope'", rules=[{"when": {"nope": 1}, "to": {"team": "x"}}])
    _bad("not defined under 'teams'", rules=[{"to": {"team": "ghost"}}])
    _bad("unknown operator", rules=[{"when": {"tag": {"bigger": 1}}, "to": {"team": "x"}}])
    _bad("exactly one of", rules=[{"to": {"team": "x", "queue": "q"}}])
    _bad("needs at least one rule", rules=[])
    _bad("is built in", fields={"email": {"type": "string"}})
    _bad("must be one of", fields={"tag": {"type": "color"}})
    _bad("needs a list of 'values'", fields={"tag": {"type": "choice"}})
    _bad("non-empty list of 'reps'", teams={"x": {"reps": []}})
    _bad("{zzz} is not a known field", rules=[{"to": {"team": "x"}, "label": "{zzz}"}])
    _bad("clashes", derived={"tag": {"from": "tag", "map": {}}})
