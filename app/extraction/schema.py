from typing import Literal

from pydantic import BaseModel, Field


class Lead(BaseModel):
    name: str | None = None
    company: str | None = None
    role: str | None = None
    intent: Literal["pricing", "demo", "support", "partnership", "spam", "other"] = "other"
    urgency: Literal["low", "medium", "high"] = "medium"
    region: str | None = Field(default=None, description="Region or country mentioned")
    country: str | None = Field(default=None, description="ISO 3166-1 alpha-2 code if known")
    employee_count: int | None = None
    email: str | None = None
    phone: str | None = None
    domain: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
