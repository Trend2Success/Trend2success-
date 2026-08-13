"""Stage 3: Personalized message — drafts outreach copy for prospects with a confirmed lead-leak."""

from __future__ import annotations

from trend2success.hvac.models import HVACProspect, LeadLeakResult, OutreachMessage


class MessageAgent:
    def run(self, prospects: list[HVACProspect], leak_results: list[LeadLeakResult]) -> list[OutreachMessage]:
        results_by_id = {r.prospect_id: r for r in leak_results}
        messages = []
        for prospect in prospects:
            result = results_by_id.get(prospect.id)
            if result is None or not result.is_leaking:
                continue

            reason = result.signals[0]
            body = (
                f"Hi {prospect.name}, we ran a quick check on {prospect.address} and noticed {reason}. "
                "That's likely costing you money every month. Want a free 20-minute audit to confirm "
                "and see what it'd take to fix it?"
            )
            messages.append(
                OutreachMessage(
                    prospect_id=prospect.id,
                    channel="email",
                    subject=f"{prospect.name}, your HVAC system may be leaking money",
                    body=body,
                )
            )
        return messages
