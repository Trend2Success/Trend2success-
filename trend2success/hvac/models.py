"""Core data models for the HVAC sales funnel.

25 HVAC prospects -> 2-minute lead-leak check -> personalized message ->
20-minute audit call -> $2,000 installation -> $350/month support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    NEW = "new"
    LEAK_CONFIRMED = "leak_confirmed"
    NO_LEAK = "no_leak"
    MESSAGED = "messaged"
    AUDIT_SCHEDULED = "audit_scheduled"
    INSTALLED = "installed"
    SUPPORT_ACTIVE = "support_active"
    LOST = "lost"


@dataclass
class HVACProspect:
    id: str
    name: str
    address: str
    phone: str
    email: str
    system_age_years: int
    monthly_bill: float
    sqft: int
    status: LeadStatus = LeadStatus.NEW


@dataclass
class LeadLeakResult:
    prospect_id: str
    is_leaking: bool
    leak_score: float
    signals: list[str] = field(default_factory=list)


@dataclass
class OutreachMessage:
    prospect_id: str
    channel: str
    subject: str
    body: str


@dataclass
class AuditCall:
    prospect_id: str
    scheduled_at: datetime
    duration_minutes: int = 20


@dataclass
class InstallationDeal:
    prospect_id: str
    amount: float
    closed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SupportSubscription:
    prospect_id: str
    monthly_amount: float
    started_at: datetime = field(default_factory=datetime.utcnow)
