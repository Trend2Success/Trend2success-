"""Application Queue — a small JSON-file-backed store for queued applications."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from trend2success.models import Application, ApplicationStatus, JobListing

DEFAULT_PATH = Path("data/application_queue.json")


def _listing_to_dict(listing: JobListing) -> dict:
    return {
        "id": listing.id,
        "title": listing.title,
        "company": listing.company,
        "url": listing.url,
        "description": listing.description,
        "source": listing.source,
        "salary": listing.salary,
        "posted_at": listing.posted_at.isoformat(),
    }


def _listing_from_dict(data: dict) -> JobListing:
    return JobListing(
        id=data["id"],
        title=data["title"],
        company=data["company"],
        url=data["url"],
        description=data["description"],
        source=data["source"],
        salary=data.get("salary"),
        posted_at=datetime.fromisoformat(data["posted_at"]),
    )


def _application_to_dict(application: Application) -> dict:
    return {
        "id": application.id,
        "listing": _listing_to_dict(application.listing),
        "match_score": application.match_score,
        "status": application.status.value,
        "created_at": application.created_at.isoformat(),
    }


def _application_from_dict(data: dict) -> Application:
    return Application(
        id=data["id"],
        listing=_listing_from_dict(data["listing"]),
        match_score=data["match_score"],
        status=ApplicationStatus(data["status"]),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


class QueueStore:
    """Persists the application queue to a JSON file, keyed by application id."""

    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, records: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def add(self, application: Application) -> None:
        records = self._load()
        records[application.id] = _application_to_dict(application)
        self._save(records)

    def get(self, application_id: str) -> Application | None:
        records = self._load()
        data = records.get(application_id)
        return _application_from_dict(data) if data else None

    def list(self) -> list[Application]:
        records = self._load()
        return [_application_from_dict(data) for data in records.values()]

    def update_status(self, application_id: str, status: ApplicationStatus) -> None:
        records = self._load()
        if application_id not in records:
            raise KeyError(f"no application queued with id {application_id!r}")
        records[application_id]["status"] = status.value
        self._save(records)
