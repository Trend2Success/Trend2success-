"""Core data models shared across the sales funnel pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DealStage(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    DEMO_SCHEDULED = "demo_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ONBOARDED = "onboarded"


@dataclass
class ICPProfile:
    """Describes the Ideal Customer Profile, used by the score/rank agent."""

    name: str
    industries: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    min_budget: int | None = None
    min_company_size: int | None = None


@dataclass
class Lead:
    id: str
    company: str
    contact_name: str
    email: str
    industry: str
    source: str
    notes: str = ""
    budget: int | None = None
    company_size: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QualificationResult:
    lead_id: str
    is_qualified: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class LeadScore:
    lead_id: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class Deal:
    id: str
    lead: Lead
    fit_score: float
    stage: DealStage = DealStage.NEW
    value: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OutreachTouch:
    deal_id: str
    channel: str  # "email", "call", "linkedin", ...
    sent_at: datetime
    message: str = ""


@dataclass
class DemoEvent:
    deal_id: str
    scheduled_at: datetime
    notes: str = ""


@dataclass
class ClosingEvent:
    deal_id: str
    closed_at: datetime
    outcome: str  # "won", "lost", "negotiating"
    value: int | None = None
    notes: str = ""


@dataclass
class FollowUp:
    deal_id: str
    followed_up_at: datetime
    outcome: str
    notes: str = ""
