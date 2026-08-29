"""Monte Carlo Expected Value simulator.

For each candidate lineup we simulate ``n_iterations`` slate outcomes:

1. Every player's fantasy score is drawn from ``Normal(mean=projection,
   std=std_dev)`` (or a fat-tailed Student-t alternative), clipped to
   ``[floor, ceiling]``. An optional shared per-team latent factor adds a
   configurable amount of same-team correlation, which is what makes
   stacks (e.g. QB + WR1) score in a genuinely correlated way rather than
   as independent draws.
2. A same-sized "field" of opponent lineups is approximated each iteration
   by sampling, independently per roster slot, a player weighted by that
   player's projected ownership. This keeps the simulation tractable (we
   don't need every opposing lineup to itself satisfy the salary cap — DK
   fields are large and heterogeneous, so a slot-independent ownership
   sample is a standard, cheap proxy for the field's score distribution)
   while still being sensitive to *this* slate's ownership shape.
3. The candidate's rank against the sampled field is scaled up to the
   contest's full ``field_size`` and looked up in the payout structure.

EV = mean prize across iterations. See :class:`SimulationResult` for the
full set of reported statistics.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dk_ev.domain import Lineup, Player
from dk_ev.payouts import PayoutStructure
from dk_ev.rules import SportRules

try:
    from numba import njit, prange

    _HAS_NUMBA = True
except ImportError:  # pragma: no cover - exercised only when numba is absent
    _HAS_NUMBA = False


if _HAS_NUMBA:

    @njit(parallel=True, cache=True)
    def _count_beaten_numba(field_scores, candidate_scores):
        n_iterations, field_sample_size = field_scores.shape
        out = np.empty(n_iterations, dtype=np.int64)
        for i in prange(n_iterations):
            c = candidate_scores[i]
            cnt = 0
            for m in range(field_sample_size):
                if field_scores[i, m] > c:
                    cnt += 1
            out[i] = cnt
        return out


def _count_beaten_numpy(field_scores: np.ndarray, candidate_scores: np.ndarray) -> np.ndarray:
    return np.sum(field_scores > candidate_scores[:, None], axis=1)


@dataclass
class SimulatorConfig:
    n_iterations: int = 10_000
    field_sample_size: int = 300
    distribution: str = "normal"  # "normal" or "student_t"
    student_t_df: float = 5.0
    team_correlation: float = 0.15
    random_seed: int | None = None
    use_numba: bool = True
    # On deep slates (hundreds of marginal players, e.g. CFB/MLB), sampling
    # a field lineup's slot from the *entire* eligible pool means every
    # phantom opponent has real odds of drawing several irrelevant players
    # regardless of how small each one's individual ownership is -- 400
    # players at 0.2% apiece is 80% of the draw. That systematically makes
    # the simulated field weaker than a real one (real opponents don't
    # roster $3,000 zero-projection bench players in appreciable numbers).
    # Truncating each slot's field-sampling pool to the players covering
    # this fraction of that slot's total ownership keeps field composition
    # realistic without touching the candidate list used by the optimizer.
    field_pool_coverage: float = 0.99


@dataclass
class SimulationResult:
    lineup: Lineup
    ev: float
    ev_net: float
    itm_pct: float
    win_pct: float
    median_rank: float
    top1_pct_rate: float
    top10_pct_rate: float
    mean_score: float
    ceiling: float
    floor: float


class EVSimulator:
    """Runs Monte Carlo EV simulation for lineups drawn from ``player_pool``."""

    def __init__(
        self,
        player_pool: list[Player],
        rules: SportRules,
        payout: PayoutStructure,
        config: SimulatorConfig | None = None,
    ):
        if not player_pool:
            raise ValueError("player_pool must not be empty")
        self.players = player_pool
        self.rules = rules
        self.payout = payout
        self.config = config or SimulatorConfig()
        self._rng = np.random.default_rng(self.config.random_seed)
        self._prepare_pool()

    def _prepare_pool(self) -> None:
        self.player_index = {p.player_id: i for i, p in enumerate(self.players)}
        self.means = np.array([p.projected_points for p in self.players], dtype=float)
        self.stds = np.array([max(p.std_dev, 1e-6) for p in self.players], dtype=float)
        self.floors = np.array([p.floor for p in self.players], dtype=float)
        self.ceilings = np.array([p.ceiling for p in self.players], dtype=float)

        teams = [p.team for p in self.players]
        unique_teams = sorted(set(teams))
        team_index = {t: i for i, t in enumerate(unique_teams)}
        self.team_ids = np.array([team_index[t] for t in teams], dtype=int)
        self.n_teams = len(unique_teams)

        self.slot_eligible_idx: list[np.ndarray] = []
        self.slot_weights: list[np.ndarray] = []
        for slot in self.rules.slots:
            idx = [
                i
                for i, p in enumerate(self.players)
                if self.rules.player_eligible_for_slot(p.positions, slot)
            ]
            if not idx:
                raise ValueError(f"No players eligible for slot {slot!r} in the player pool")
            weights = np.array(
                [max(self.players[i].ownership_pct, 0.01) for i in idx], dtype=float
            )
            idx, weights = self._truncate_to_coverage(np.array(idx), weights)
            weights = weights / weights.sum()
            self.slot_eligible_idx.append(idx)
            self.slot_weights.append(weights)

    def _truncate_to_coverage(
        self, idx: np.ndarray, weights: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        coverage = self.config.field_pool_coverage
        min_keep = min(len(idx), 5)
        if coverage >= 1.0 or len(idx) <= min_keep:
            return idx, weights
        order = np.argsort(weights)[::-1]
        cum = np.cumsum(weights[order])
        cutoff = max(min_keep, int(np.searchsorted(cum, coverage * cum[-1]) + 1))
        keep = order[:cutoff]
        return idx[keep], weights[keep]

    def _simulate_player_scores(self, n_iterations: int) -> np.ndarray:
        rng = self._rng
        cfg = self.config
        n_players = len(self.players)

        if cfg.distribution == "student_t":
            raw = rng.standard_t(cfg.student_t_df, size=(n_iterations, n_players))
            scale = self.stds / np.sqrt(cfg.student_t_df / (cfg.student_t_df - 2))
            scores = self.means + raw * scale
        else:
            scores = rng.normal(self.means, self.stds, size=(n_iterations, n_players))

        if cfg.team_correlation > 0 and self.n_teams > 0:
            team_factors = rng.normal(0.0, 1.0, size=(n_iterations, self.n_teams))
            player_team_factor = team_factors[:, self.team_ids]
            scores = scores + player_team_factor * (self.stds * cfg.team_correlation)

        return np.clip(scores, self.floors, self.ceilings)

    def _simulate_field_scores(self, player_scores: np.ndarray) -> np.ndarray:
        n_iterations = player_scores.shape[0]
        m = self.config.field_sample_size
        rng = self._rng
        field_scores = np.zeros((n_iterations, m))
        iter_idx = np.arange(n_iterations)[:, None]
        for idx_pool, weights in zip(self.slot_eligible_idx, self.slot_weights):
            picks = rng.choice(len(idx_pool), size=(n_iterations, m), p=weights)
            chosen_players = idx_pool[picks]
            field_scores += player_scores[iter_idx, chosen_players]
        return field_scores

    def _lineup_indices(self, lineup: Lineup) -> np.ndarray:
        try:
            return np.array([self.player_index[p.player_id] for p in lineup.players])
        except KeyError as exc:
            raise ValueError(
                f"Lineup contains a player not in the simulator's pool: {exc}"
            ) from exc

    def simulate(self, lineup: Lineup) -> SimulationResult:
        cfg = self.config
        player_scores = self._simulate_player_scores(cfg.n_iterations)
        candidate_scores = player_scores[:, self._lineup_indices(lineup)].sum(axis=1)
        field_scores = self._simulate_field_scores(player_scores)

        if _HAS_NUMBA and cfg.use_numba:
            beaten = _count_beaten_numba(field_scores, candidate_scores)
        else:
            beaten = _count_beaten_numpy(field_scores, candidate_scores)

        m = field_scores.shape[1]
        percentile_beaten = beaten / m
        implied_rank = np.clip(
            np.round(percentile_beaten * (self.payout.field_size - 1)) + 1,
            1,
            self.payout.field_size,
        ).astype(int)

        prizes = self.payout.prizes_for_ranks(implied_rank)
        top1_cut = max(1, round(self.payout.field_size * 0.01))
        top10_cut = max(1, round(self.payout.field_size * 0.10))

        return SimulationResult(
            lineup=lineup,
            ev=float(prizes.mean()),
            ev_net=float(prizes.mean() - self.payout.entry_fee),
            itm_pct=float(np.mean(prizes > 0)),
            win_pct=float(np.mean(implied_rank == 1)),
            median_rank=float(np.median(implied_rank)),
            top1_pct_rate=float(np.mean(implied_rank <= top1_cut)),
            top10_pct_rate=float(np.mean(implied_rank <= top10_cut)),
            mean_score=float(candidate_scores.mean()),
            ceiling=float(np.percentile(candidate_scores, 90)),
            floor=float(np.percentile(candidate_scores, 10)),
        )

    def simulate_many(self, lineups: list[Lineup]) -> list[SimulationResult]:
        return [self.simulate(lu) for lu in lineups]
