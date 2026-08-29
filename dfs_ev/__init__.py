"""NCAAF DFS EV Optimizer.

A CLI tool that ranks NCAAF DFS lineups by simulated expected ROI rather than
raw projected points. DraftKings/FanDuel contest CSVs are the source of truth
for salaries and roster rules; OpticOdds API v3 supplies odds, props,
injuries, and historical results.
"""

__version__ = "0.1.0"
