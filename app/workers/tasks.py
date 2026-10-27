import logging
import time

from app.config import get_settings
from app.db.models import LeadRecord, RoutingDecision
from app.db.session import SessionLocal
from app.enrichment import enrich
from app.extraction.extractor import REFUSED_MODEL, LLMUnavailable, extract_lead_with_model
from app.integrations.crm import CRMUnavailable, get_crm
from app.integrations.slack import notify
from app.profile import get_profile
from app.routing.engine import route, with_derived
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

        profile = get_profile()
        lead, llm_model = extract_lead_with_model(rec.sender, rec.subject, rec.body)
        facts = lead.model_dump()
        enrichment = enrich(lead.domain, db) if profile.enrich_fill else {}
        for field in profile.enrich_fill:  # the email's own facts win over the lookup
            if facts.get(field) in (None, ""):
                facts[field] = enrichment.get(field)

        decision = route(
            facts=facts,
            confidence=lead.confidence,
            refused=llm_model == REFUSED_MODEL,
            profile=profile,
            threshold=settings.confidence_threshold,
            pick_rep=make_db_picker(db),
        )

        title = (facts.get(profile.title_field or "") or lead.email or rec.sender) or "unknown"
        deal_id = deal_url = None
        if profile.crm and decision.rep and lead.email:
            first, _, last = (facts.get("name") or "").partition(" ")
            crm = get_crm()
            contact_id = crm.upsert_contact(
                lead.email,
                {
                    "firstname": first,
                    "lastname": last,
                    "company": facts.get("company"),
                    "jobtitle": facts.get("role"),
                    "phone": lead.phone,
                },
                owner=decision.rep,
            )
            deal_id = crm.create_deal(
                contact_id, f"{facts.get('company') or lead.domain} inquiry", owner=decision.rep
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

        if profile.slack:
            full = with_derived(profile, facts)
            details = " ".join(
                f"{f}={full[f]}" for f in profile.summary_fields if full.get(f) is not None
            )
            message = (
                f"New {profile.item_name}: {title}"
                + (f" | {details}" if details else "")
                + f" | assigned={decision.rep or decision.team} ({decision.rule})"
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
