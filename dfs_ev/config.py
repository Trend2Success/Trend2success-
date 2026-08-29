"""Environment/config loading for the DFS EV Optimizer.

OpticOdds API key is read from OPTICODDS_API_KEY and never logged or
otherwise surfaced in output.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "data" / "dfs_ev.sqlite3"


@dataclass(frozen=True)
class Settings:
    opticodds_api_key: str | None = field(default_factory=lambda: os.getenv("OPTICODDS_API_KEY"))
    opticodds_base_url: str = field(
        default_factory=lambda: os.getenv("OPTICODDS_BASE_URL", "https://api.opticodds.com/api/v3")
    )
    db_path: str = field(default_factory=lambda: os.getenv("DFS_EV_DB_PATH", str(DEFAULT_DB_PATH)))
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("OPTICODDS_CACHE_TTL_SECONDS", "900"))
    )
    max_calls_per_slate: int = field(
        default_factory=lambda: int(os.getenv("OPTICODDS_MAX_CALLS_PER_SLATE", "200"))
    )
    historical_rate_limit_per_min: int = 40
    default_rate_limit_per_min: int = 10_000
    max_books_per_call: int = 5
    max_ids_per_call: int = 5

    def require_api_key(self) -> str:
        if not self.opticodds_api_key:
            raise RuntimeError(
                "OPTICODDS_API_KEY is not set. Add it to your environment or .env file."
            )
        return self.opticodds_api_key


def get_settings() -> Settings:
    return Settings()
