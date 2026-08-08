"""Core data models shared across the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    QUEUED = "queued"
    SUBMITTED = "submitted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    FOLLOWED_UP = "followed_up"
    REJECTED = "rejected"
    OFFER = "offer"


@dataclass
class CandidateProfile:
    """Describes what the candidate is looking for, used by the match/rank agent."""

    name: str
    skills: list[str]
    keywords: list[str] = field(default_factory=list)
    min_salary: int | None = None


@dataclass
class JobListing:
    id: str
    title: str
    company: str
    url: str
    description: str
    source: str
    salary: int | None = None
    posted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VerificationResult:
    listing_id: str
    is_valid: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class MatchScore:
    listing_id: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class Application:
    id: str
    listing: JobListing
    match_score: float
    status: ApplicationStatus = ApplicationStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterviewEvent:
    application_id: str
    kind: str  # "interview" or "sales_call"
    scheduled_at: datetime
    notes: str = ""


@dataclass
class FollowUp:
    application_id: str
    followed_up_at: datetime
    outcome: str
    notes: str = ""
