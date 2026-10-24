"""GET /metrics in Prometheus text format, computed from Postgres on each scrape.

Reading the database (instead of keeping in-process counters) keeps the numbers correct
across the API and every worker process, and across restarts.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import LeadRecord, RoutingDecision
from app.db.session import get_db

router = APIRouter()

LATENCY_WINDOW = 500  # most recent decisions used for the processing-time quantiles


def _label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _series(lines: list[str], name: str, kind: str, help_: str, rows, label: str) -> None:
    lines += [f"# HELP {name} {help_}", f"# TYPE {name} {kind}"]
    for key, count in rows:
        lines.append(f'{name}{{{label}="{_label(key)}"}} {count}')


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)) -> PlainTextResponse:
    lines: list[str] = []

    def grouped(column, table):
        return db.execute(select(column, func.count()).select_from(table).group_by(column)).all()

    _series(lines, "switchboard_leads_total", "counter", "Leads by status.",
            grouped(LeadRecord.status, LeadRecord), "status")
    _series(lines, "switchboard_routing_decisions_total", "counter",
            "Routing decisions by rule that fired.",
            grouped(RoutingDecision.rule, RoutingDecision), "rule")
    _series(lines, "switchboard_leads_by_rep_total", "counter",
            "Routing decisions by assigned rep (or team for the review queue).",
            grouped(RoutingDecision.rep, RoutingDecision), "rep")
    answered = [(m or "none", c) for m, c in grouped(LeadRecord.llm_model, LeadRecord)]
    _series(lines, "switchboard_llm_answers_total", "counter",
            "Leads by the model that answered.", answered, "model")

    rows = db.execute(
        select(LeadRecord.created_at, RoutingDecision.created_at)
        .join(RoutingDecision, RoutingDecision.lead_id == LeadRecord.id)
        .order_by(RoutingDecision.created_at.desc())
        .limit(LATENCY_WINDOW)
    ).all()
    seconds = sorted((done - start).total_seconds() for start, done in rows)
    lines += [
        "# HELP switchboard_processing_seconds Time from ingest to routing decision "
        f"over the last {LATENCY_WINDOW} decisions.",
        "# TYPE switchboard_processing_seconds gauge",
    ]
    for name, q in (("p50", 0.5), ("p95", 0.95)):
        value = _quantile(seconds, q)
        lines.append(f'switchboard_processing_seconds{{quantile="{name}"}} {value:.3f}')

    return PlainTextResponse(
        "\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8"
    )
