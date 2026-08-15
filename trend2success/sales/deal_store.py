"""Deal Pipeline — a small JSON-file-backed CRM store for deals in flight."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from trend2success.sales.models import Deal, DealStage, Lead

DEFAULT_PATH = Path("data/deal_pipeline.json")


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "company": lead.company,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "industry": lead.industry,
        "source": lead.source,
        "notes": lead.notes,
        "budget": lead.budget,
        "company_size": lead.company_size,
        "created_at": lead.created_at.isoformat(),
    }


def _lead_from_dict(data: dict) -> Lead:
    return Lead(
        id=data["id"],
        company=data["company"],
        contact_name=data["contact_name"],
        email=data["email"],
        industry=data["industry"],
        source=data["source"],
        notes=data.get("notes", ""),
        budget=data.get("budget"),
        company_size=data.get("company_size"),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _deal_to_dict(deal: Deal) -> dict:
    return {
        "id": deal.id,
        "lead": _lead_to_dict(deal.lead),
        "fit_score": deal.fit_score,
        "stage": deal.stage.value,
        "value": deal.value,
        "created_at": deal.created_at.isoformat(),
    }


def _deal_from_dict(data: dict) -> Deal:
    return Deal(
        id=data["id"],
        lead=_lead_from_dict(data["lead"]),
        fit_score=data["fit_score"],
        stage=DealStage(data["stage"]),
        value=data.get("value"),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


class DealStore:
    """Persists the deal pipeline to a JSON file, keyed by deal id."""

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

    def add(self, deal: Deal) -> None:
        records = self._load()
        records[deal.id] = _deal_to_dict(deal)
        self._save(records)

    def get(self, deal_id: str) -> Deal | None:
        records = self._load()
        data = records.get(deal_id)
        return _deal_from_dict(data) if data else None

    def list(self) -> list[Deal]:
        records = self._load()
        return [_deal_from_dict(data) for data in records.values()]

    def update_stage(self, deal_id: str, stage: DealStage) -> None:
        records = self._load()
        if deal_id not in records:
            raise KeyError(f"no deal in pipeline with id {deal_id!r}")
        records[deal_id]["stage"] = stage.value
        self._save(records)

    def update_value(self, deal_id: str, value: int) -> None:
        records = self._load()
        if deal_id not in records:
            raise KeyError(f"no deal in pipeline with id {deal_id!r}")
        records[deal_id]["value"] = value
        self._save(records)
