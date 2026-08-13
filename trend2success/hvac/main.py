"""CLI entrypoint: run the HVAC funnel intake (25 prospects -> lead-leak check -> personalized message)."""

from __future__ import annotations

import argparse

from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.pipeline import HVACFunnel


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Trend2Success HVAC sales funnel intake.")
    parser.add_argument(
        "--lead-store-path", default="data/hvac_lead_store.json", help="Path to the lead store JSON file."
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    funnel = HVACFunnel(lead_store=LeadStore(args.lead_store_path))
    result = funnel.run()

    leaking = sum(r.is_leaking for r in result.leak_results)
    print(f"Pulled {len(result.prospects_found)} prospects, {leaking} flagged by the lead-leak check.")
    print(f"Sent {len(result.messages_sent)} personalized messages:")
    for message in result.messages_sent:
        print(f"  - [{message.prospect_id}] {message.subject}")


if __name__ == "__main__":
    main()
