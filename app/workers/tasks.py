import logging
import time

from app.config import get_settings
from app.db.models import LeadRecord, RoutingDecision
from app.db.session import SessionLocal
from app.enrichment import enrich
from app.extraction.extractor import REFUSED_MODEL, LLMUnavailable, extract_lead_with_model
from app.integrations.crm import CRMUnavailable, get_crm
from app.integrations.slack import notify
from app.routing.engine import load_rules, route
from app.routing.round_robin import make_db_picker
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


def run_pipeline(lead_id: str) -> None:
    settings = get_settings()
    started = time.monotonic()
    with SessionLocal() as db:
        rec = db.get(LeadRecord, lead_id)
        if rec is None:
            return
        rec.status = "processing"
        db.commit()

        lead, llm_model = extract_lead_with_model(rec.sender, rec.subject, rec.body)
        enrichment = enrich(lead.domain, db)
        country = lead.country or enrichment.get("country")
        employees = lead.employee_count or enrichment.get("employee_count")

        decision = route(
            country=country,
            employee_count=employees,
            confidence=lead.confidence,
            intent=lead.intent,
            refused=llm_model == REFUSED_MODEL,
            rules=load_rules(settings.routing_config_path),
            threshold=settings.confidence_threshold,
            pick_rep=make_db_picker(db),
        )

        deal_id = deal_url = None
        if decision.rep and lead.email:
            first, _, last = (lead.name or "").partition(" ")
            crm = get_crm()
            contact_id = crm.upsert_contact(
                lead.email,
                {
                    "firstname": first,
                    "lastname": last,
                    "company": lead.company,
                    "jobtitle": lead.role,
                    "phone": lead.phone,
                },
                owner=decision.rep,
            )
            deal_id = crm.create_deal(
                contact_id, f"{lead.company or lead.domain} inquiry", owner=decision.rep
            )
            deal_url = crm.deal_url(deal_id)

        rec.parsed = lead.model_dump()
        rec.llm_model = llm_model
        rec.enrichment = enrichment
        rec.decision = {**decision.to_dict(), "deal_id": deal_id}
        rec.status = "review" if decision.rep is None else "routed"
        db.add(
            RoutingDecision(
                lead_id=rec.id,
                rep=decision.rep or decision.team,
                rule=decision.rule,
                confidence=decision.confidence,
            )
        )
        db.commit()

        log.info(
            "lead processed",
            extra={
                "lead_id": rec.id,
                "outcome": rec.status,
                "rule": decision.rule,
                "rep": decision.rep,
                "llm_model": llm_model,
                "confidence": lead.confidence,
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        )

        size = f"{employees} employees" if employees else "size unknown"
        message = (
            f"New lead: {lead.company or lead.email} ({size}) | intent={lead.intent} "
            f"urgency={lead.urgency} | assigned={decision.rep or 'review queue'} "
            f"({decision.rule})"
        )
        if deal_url:
            message += f" | {deal_url}"
        notify(message)


def mark_failed(lead_id: str, error: str) -> None:
    with SessionLocal() as db:
        rec = db.get(LeadRecord, lead_id)
        if rec is not None:
            rec.status = "failed"
            rec.error = error[:2000]
            db.commit()


RETRYABLE = (ConnectionError, TimeoutError, LLMUnavailable, CRMUnavailable)


@celery_app.task(name="process_lead", bind=True, max_retries=40)
def process_lead(self, lead_id: str) -> None:
    try:
        run_pipeline(lead_id)
    except RETRYABLE as exc:
        retries = self.request.retries
        if isinstance(exc, LLMUnavailable):
            # Every model is out of quota: wait until the earliest reset. Capped under the
            # Redis broker's 1h visibility timeout, so a long wait is several shorter retries.
            countdown = min(max(exc.retry_after, 30), 1800)
            limit = self.max_retries
        else:
            countdown, limit = 2**retries, 5
        if retries < limit:
            raise self.retry(exc=exc, countdown=countdown) from exc
        mark_failed(lead_id, str(exc))
    except Exception as exc:
        log.exception("lead failed", extra={"lead_id": lead_id})
        mark_failed(lead_id, f"{type(exc).__name__}: {exc}")
