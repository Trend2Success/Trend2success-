"""CLI entrypoint: run the full search -> verify -> match & rank -> queue flow."""

from __future__ import annotations

import argparse

from trend2success.models import CandidateProfile
from trend2success.pipeline import Pipeline
from trend2success.queue_store import QueueStore


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Trend2Success multi-agent application pipeline.")
    parser.add_argument("--query", default="engineer", help="Search query passed to the search agent.")
    parser.add_argument("--name", default="Candidate", help="Candidate name.")
    parser.add_argument("--skills", default="", help="Comma-separated skills, e.g. 'python,django,sql'.")
    parser.add_argument("--keywords", default="", help="Comma-separated extra keywords to match on.")
    parser.add_argument("--min-salary", type=int, default=None, help="Minimum acceptable salary.")
    parser.add_argument("--top-n", type=int, default=5, help="Max number of applications to queue.")
    parser.add_argument("--queue-path", default="data/application_queue.json", help="Path to the queue JSON file.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    profile = CandidateProfile(
        name=args.name,
        skills=[s.strip() for s in args.skills.split(",") if s.strip()],
        keywords=[k.strip() for k in args.keywords.split(",") if k.strip()],
        min_salary=args.min_salary,
    )

    pipeline = Pipeline(top_n=args.top_n, queue_store=QueueStore(args.queue_path))
    result = pipeline.run(args.query, profile)

    print(f"Found {len(result.listings_found)} listings, "
          f"{sum(r.is_valid for r in result.verification_results)} passed verification.")
    print(f"Ranked {len(result.match_scores)} listings, queued {len(result.applications_queued)} applications:")
    for application in result.applications_queued:
        listing = application.listing
        print(f"  - [{application.match_score:.2f}] {listing.title} @ {listing.company} ({listing.url})")


if __name__ == "__main__":
    main()
