from itertools import count

from app.routing.engine import load_rules, route

RULES = load_rules("config/routing.yaml")


def _picker():
    n = count()
    return lambda team, reps: reps[next(n) % len(reps)]


def _route(**kw):
    args = dict(country="SG", employee_count=200, confidence=0.9, rules=RULES,
                threshold=0.7, pick_rep=_picker())
    args.update(kw)
    return route(**args)


def test_smb_in_territory():
    d = _route()
    assert d.team == "smb" and d.rep == "alice"
    assert d.rule == "territory:APAC+segment:smb+round_robin"


def test_enterprise_segment():
    d = _route(employee_count=5000, country="US")
    assert d.team == "enterprise" and d.rep == "carol"


def test_round_robin_cycles():
    pick = _picker()
    reps = [_route(pick_rep=pick).rep for _ in range(3)]
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
