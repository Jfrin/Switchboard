from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass
class Decision:
    team: str
    rep: str | None
    rule: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def load_rules(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def region_for(country: str | None, rules: dict) -> str | None:
    if not country:
        return None
    for region, countries in rules["territories"].items():
        if country.upper() in countries:
            return region
    return None


def segment_for(employee_count: int | None, rules: dict) -> str | None:
    if employee_count is None:
        return None
    threshold = rules["segments"]["enterprise_min_employees"]
    return "enterprise" if employee_count >= threshold else "smb"


def route(
    *,
    country: str | None,
    employee_count: int | None,
    confidence: float,
    rules: dict,
    threshold: float,
    pick_rep: Callable[[str, list[str]], str],
) -> Decision:
    """Territory -> segment -> round-robin. Anything unclear goes to the review queue."""
    fallback = rules["fallback_queue"]
    if confidence < threshold:
        return Decision(fallback, None, "fallback:low_confidence", confidence)

    region = region_for(country, rules)
    if region is None:
        return Decision(fallback, None, "fallback:no_territory", confidence)

    segment = segment_for(employee_count, rules)
    if segment is None:
        return Decision(fallback, None, "fallback:no_segment", confidence)

    reps = rules["teams"][segment]["reps"]
    rep = pick_rep(segment, reps)
    return Decision(segment, rep, f"territory:{region}+segment:{segment}+round_robin", confidence)
