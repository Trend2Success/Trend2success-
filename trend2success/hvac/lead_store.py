"""HVAC lead store — a small JSON-file-backed store for prospects moving through the funnel."""

from __future__ import annotations

import json
from pathlib import Path

from trend2success.hvac.models import HVACProspect, LeadStatus

DEFAULT_PATH = Path("data/hvac_lead_store.json")


def _prospect_to_dict(prospect: HVACProspect) -> dict:
    return {
        "id": prospect.id,
        "name": prospect.name,
        "address": prospect.address,
        "phone": prospect.phone,
        "email": prospect.email,
        "system_age_years": prospect.system_age_years,
        "monthly_bill": prospect.monthly_bill,
        "sqft": prospect.sqft,
        "status": prospect.status.value,
    }


def _prospect_from_dict(data: dict) -> HVACProspect:
    return HVACProspect(
        id=data["id"],
        name=data["name"],
        address=data["address"],
        phone=data["phone"],
        email=data["email"],
        system_age_years=data["system_age_years"],
        monthly_bill=data["monthly_bill"],
        sqft=data["sqft"],
        status=LeadStatus(data["status"]),
    )


class LeadStore:
    """Persists HVAC prospects to a JSON file, keyed by prospect id."""

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

    def add(self, prospect: HVACProspect) -> None:
        records = self._load()
        records[prospect.id] = _prospect_to_dict(prospect)
        self._save(records)

    def get(self, prospect_id: str) -> HVACProspect | None:
        records = self._load()
        data = records.get(prospect_id)
        return _prospect_from_dict(data) if data else None

    def list(self) -> list[HVACProspect]:
        records = self._load()
        return [_prospect_from_dict(data) for data in records.values()]

    def update_status(self, prospect_id: str, status: LeadStatus) -> None:
        records = self._load()
        if prospect_id not in records:
            raise KeyError(f"no prospect with id {prospect_id!r}")
        records[prospect_id]["status"] = status.value
        self._save(records)
