"""Orchestrates the HVAC funnel intake: 25 HVAC prospects -> lead-leak check -> personalized message.

The audit call, installation, and support stages happen afterwards, on their own
schedule (see audit_scheduler.py / installation.py / support.py), since they depend
on real-world events (a call happening, a deal closing) that don't happen
synchronously with lead intake.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trend2success.hvac.lead_leak_agent import LeadLeakAgent
from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.message_agent import MessageAgent
from trend2success.hvac.models import HVACProspect, LeadLeakResult, LeadStatus, OutreachMessage
from trend2success.hvac.prospect_source import ProspectSource


@dataclass
class HVACFunnelResult:
    prospects_found: list[HVACProspect] = field(default_factory=list)
    leak_results: list[LeadLeakResult] = field(default_factory=list)
    messages_sent: list[OutreachMessage] = field(default_factory=list)


class HVACFunnel:
    def __init__(
        self,
        prospect_source: ProspectSource | None = None,
        lead_leak_agent: LeadLeakAgent | None = None,
        message_agent: MessageAgent | None = None,
        lead_store: LeadStore | None = None,
    ) -> None:
        self.prospect_source = prospect_source or ProspectSource()
        self.lead_leak_agent = lead_leak_agent or LeadLeakAgent()
        self.message_agent = message_agent or MessageAgent()
        self.lead_store = lead_store or LeadStore()

    def run(self) -> HVACFunnelResult:
        prospects = self.prospect_source.run()
        for prospect in prospects:
            self.lead_store.add(prospect)

        leak_results = self.lead_leak_agent.run(prospects)
        for result in leak_results:
            status = LeadStatus.LEAK_CONFIRMED if result.is_leaking else LeadStatus.NO_LEAK
            self.lead_store.update_status(result.prospect_id, status)

        messages = self.message_agent.run(prospects, leak_results)
        for message in messages:
            self.lead_store.update_status(message.prospect_id, LeadStatus.MESSAGED)

        return HVACFunnelResult(prospects_found=prospects, leak_results=leak_results, messages_sent=messages)
