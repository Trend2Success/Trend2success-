"""Stage 2: Qualify — filters out leads that fail basic BANT-style qualification."""

from __future__ import annotations

from trend2success.sales.models import Lead, QualificationResult


class QualifyAgent:
    def run(self, leads: list[Lead]) -> list[QualificationResult]:
        seen_emails: set[str] = set()
        results = []
        for lead in leads:
            reasons = []
            if not lead.contact_name.strip():
                reasons.append("missing contact name")
            if not lead.company.strip():
                reasons.append("missing company")
            if "@" not in lead.email or "." not in lead.email.split("@")[-1]:
                reasons.append("invalid email")
            if lead.budget is None or lead.budget <= 0:
                reasons.append("no budget specified")
            if lead.email in seen_emails:
                reasons.append("duplicate email")
            seen_emails.add(lead.email)

            results.append(QualificationResult(lead_id=lead.id, is_qualified=not reasons, reasons=reasons))
        return results
