import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LeadRecord
from app.db.session import get_db

router = APIRouter()


class LeadIn(BaseModel):
    sender: str = Field(alias="from")
    subject: str = ""
    body: str

    model_config = {"populate_by_name": True}


class LeadAccepted(BaseModel):
    id: str
    status: str


class LeadOut(BaseModel):
    id: str
    sender: str
    subject: str
    status: str
    parsed: dict | None = None
    decision: dict | None = None
    error: str | None = None
    llm_model: str | None = None
    created_at: datetime


def _to_out(rec: LeadRecord) -> LeadOut:
    return LeadOut(
        id=rec.id,
        sender=rec.sender,
        subject=rec.subject,
        status=rec.status,
        parsed=rec.parsed,
        decision=rec.decision,
        error=rec.error,
        llm_model=rec.llm_model,
        created_at=rec.created_at,
    )


@router.post("/leads", status_code=202, response_model=LeadAccepted)
def create_lead(payload: LeadIn, db: Session = Depends(get_db)) -> LeadAccepted:
    rec = LeadRecord(
        id=str(uuid.uuid4()),
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        status="queued",
    )
    db.add(rec)
    db.commit()

    # Imported lazily so the API can start (and tests can run) without a broker.
    from app.workers.tasks import process_lead

    process_lead.delay(rec.id)
    return LeadAccepted(id=rec.id, status=rec.status)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, db: Session = Depends(get_db)) -> LeadOut:
    rec = db.get(LeadRecord, lead_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return _to_out(rec)


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    status: str | None = None,
    rep: str | None = None,
    since: datetime | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[LeadOut]:
    stmt = select(LeadRecord).order_by(LeadRecord.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(LeadRecord.status == status)
    if since:
        stmt = stmt.where(LeadRecord.created_at >= since)
    rows = db.scalars(stmt).all()
    if rep:
        rows = [r for r in rows if (r.decision or {}).get("rep") == rep]
    return [_to_out(r) for r in rows]
