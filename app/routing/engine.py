"""Generic rule engine: derived fields, then ordered rules, first match wins.

Everything unclear goes to the profile's fallback queue with a label that says why.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from app.profile import TEMPLATE, Profile


@dataclass
class Decision:
    team: str
    rep: str | None
    rule: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def with_derived(profile: Profile, facts: dict[str, Any]) -> dict[str, Any]:
    """The extracted facts plus the profile's derived fields (None when the source is missing)."""
    out = dict(facts)
    for name, spec in profile.derived.items():
        value = facts.get(spec["from"])
        result = None
        if value is not None:
            if spec.get("map") is not None:
                for label, members in spec["map"].items():
                    if str(value).upper() in [str(m).upper() for m in members]:
                        result = label
                        break
            else:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    number = None
                if number is not None:
                    for band in spec["bands"]:
                        if number >= band["min"]:
                            result = band["value"]
                            break
        out[name] = result
    return out


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.casefold() == b.casefold()
    return a == b


def _op(op: str, value: Any, arg: Any) -> bool:
    if op == "exists":
        return (value is not None and value != "") == bool(arg)
    if value is None:
        return op == "not_in"  # a missing value is not in any list
    try:
        if op == "eq":
            return _same(value, arg)
        if op == "in":
            return any(_same(value, a) for a in arg)
        if op == "not_in":
            return not any(_same(value, a) for a in arg)
        if op == "gt":
            return value > arg
        if op == "gte":
            return value >= arg
        if op == "lt":
            return value < arg
        if op == "lte":
            return value <= arg
        if op == "contains":
            if isinstance(value, str):
                return str(arg).casefold() in value.casefold()
            return any(_same(v, arg) for v in value)
    except TypeError:
        return False
    return False


def _matches(when: dict, facts: dict[str, Any]) -> bool:
    for field, cond in (when or {}).items():
        value = facts.get(field)
        if isinstance(cond, dict):
            ops = list(cond.items())
        elif isinstance(cond, list):
            ops = [("in", cond)]
        else:
            ops = [("eq", cond)]
        if not all(_op(op, value, arg) for op, arg in ops):
            return False
    return True


def _fill(text: str, facts: dict[str, Any]) -> str:
    return TEMPLATE.sub(lambda m: str(facts.get(m.group(1)) or ""), text)


def route(
    *,
    facts: dict[str, Any],
    confidence: float,
    profile: Profile,
    threshold: float,
    pick_rep: Callable[[str, list[str]], str],
    refused: bool = False,
) -> Decision:
    """Built-in checks first (refused, low confidence), then the profile's rules in order."""
    fallback = profile.fallback_queue
    if refused:  # every model refused the message: a human reads it
        return Decision(fallback, None, "fallback:content_filtered", confidence)
    if confidence < threshold:
        return Decision(fallback, None, "fallback:low_confidence", confidence)

    full = with_derived(profile, {**facts, "confidence": confidence})
    for i, rule in enumerate(profile.rules, 1):
        if not _matches(rule.get("when"), full):
            continue
        label = _fill(rule["label"], full) if rule.get("label") else f"rule:{i}"
        kind, target = next(iter(rule["to"].items()))
        target = _fill(str(target), full)
        if kind == "queue":
            queue = fallback if target == "fallback" else target
            return Decision(queue, None, label, confidence)
        reps = profile.teams.get(target)
        if not reps:
            return Decision(fallback, None, f"fallback:unknown_team:{target}", confidence)
        return Decision(target, pick_rep(target, reps), label, confidence)
    return Decision(fallback, None, "fallback:no_match", confidence)
