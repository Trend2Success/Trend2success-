"""CLI entrypoint: run the lead gen -> qualify -> score & rank -> deal pipeline flow."""

from __future__ import annotations

import argparse

from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import ICPProfile
from trend2success.sales.pipeline import SalesPipeline


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Trend2Success sales funnel pipeline.")
    parser.add_argument("--query", default="automation", help="Search query passed to the lead-gen agent.")
    parser.add_argument("--name", default="ICP", help="Ideal Customer Profile name.")
    parser.add_argument("--industries", default="", help="Comma-separated target industries, e.g. 'SaaS,Retail'.")
    parser.add_argument("--keywords", default="", help="Comma-separated pain-point/product keywords to match on.")
    parser.add_argument("--min-budget", type=int, default=None, help="Minimum acceptable lead budget.")
    parser.add_argument("--min-company-size", type=int, default=None, help="Minimum acceptable company size.")
    parser.add_argument("--top-n", type=int, default=5, help="Max number of deals to queue into the pipeline.")
    parser.add_argument("--deals-path", default="data/deal_pipeline.json", help="Path to the deal pipeline JSON file.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    icp = ICPProfile(
        name=args.name,
        industries=[i.strip() for i in args.industries.split(",") if i.strip()],
        keywords=[k.strip() for k in args.keywords.split(",") if k.strip()],
        min_budget=args.min_budget,
        min_company_size=args.min_company_size,
    )

    pipeline = SalesPipeline(top_n=args.top_n, deal_store=DealStore(args.deals_path))
    result = pipeline.run(args.query, icp)

    print(f"Found {len(result.leads_found)} leads, "
          f"{sum(r.is_qualified for r in result.qualification_results)} passed qualification.")
    print(f"Ranked {len(result.lead_scores)} leads, queued {len(result.deals_queued)} deals:")
    for deal in result.deals_queued:
        lead = deal.lead
        print(f"  - [{deal.fit_score:.2f}] {lead.company} ({lead.contact_name}, {lead.industry}) -> {deal.stage.value}")


if __name__ == "__main__":
    main()
