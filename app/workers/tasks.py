import logging

from app.config import get_settings
from app.db.models import LeadRecord, RoutingDecision
from app.db.session import SessionLocal
from app.enrichment import enrich
from app.extraction.extractor import LLMUnavailable, extract_lead
from app.integrations.crm import get_crm
from app.integrations.slack import notify
from app.routing.engine import load_rules, route
from app.routing.round_robin import make_db_picker
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


def run_pipeline(lead_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        rec = db.get(LeadRecord, lead_id)
        if rec is None:
            return
        rec.status = "processing"
        db.commit()

        lead = extract_lead(rec.sender, rec.subject, rec.body)
        enrichment = enrich(lead.domain)
        country = lead.country or enrichment.get("country")
        employees = lead.employee_count or enrichment.get("employee_count")

        decision = route(
            country=country,
            employee_count=employees,
            confidence=lead.confidence,
            rules=load_rules(settings.routing_config_path),
            threshold=settings.confidence_threshold,
            pick_rep=make_db_picker(db),
        )

        if decision.rep and lead.email:
            crm = get_crm()
            contact_id = crm.upsert_contact(lead.email, {"company": lead.company})
            crm.create_deal(contact_id, f"{lead.company or lead.domain} inquiry", decision.rep)

        rec.parsed = lead.model_dump()
        rec.enrichment = enrichment
        rec.decision = {**decision.to_dict(), "rep": decision.rep}
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

        notify(
            f"New lead: {lead.company or lead.email} | intent={lead.intent} "
            f"urgency={lead.urgency} | assigned={decision.rep or 'review queue'} "
            f"({decision.rule})"
        )


def mark_failed(lead_id: str, error: str) -> None:
    with SessionLocal() as db:
        rec = db.get(LeadRecord, lead_id)
        if rec is not None:
            rec.status = "failed"
            rec.error = error[:2000]
            db.commit()


RETRYABLE = (ConnectionError, TimeoutError, LLMUnavailable)


@celery_app.task(name="process_lead", bind=True, max_retries=5)
def process_lead(self, lead_id: str) -> None:
    try:
        run_pipeline(lead_id)
    except RETRYABLE as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
        mark_failed(lead_id, str(exc))
    except Exception as exc:
        log.exception("lead %s failed", lead_id)
        mark_failed(lead_id, f"{type(exc).__name__}: {exc}")
