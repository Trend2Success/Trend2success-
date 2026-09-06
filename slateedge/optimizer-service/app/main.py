"""
SlateEdge optimizer-service: a standalone Python analytics microservice.

This is an independent, personal-use decision-support tool for NFL DFS
lineup construction. It is NOT affiliated with, endorsed by, or associated
with DraftKings or any other daily fantasy sports operator. It does not
scrape any operator's site and copies no branding. All numbers it returns
(projections, ownership, simulated outcomes, "risk" scores, etc.) are
ESTIMATES produced from user-supplied inputs and standard statistical/
optimization techniques -- never guarantees of real-world results.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import OptimizeRequest, OptimizeResponse, SimulateRequest, SimulateResponse
from .optimizer import generate_lineups
from .simulation import run_simulation

app = FastAPI(
    title="SlateEdge Optimizer Service",
    description=(
        "Independent, personal-use DFS decision-support analytics service. "
        "Not affiliated with DraftKings or any other operator. All outputs "
        "are estimates, not guarantees."
    ),
    version="1.0.0",
)

# CORS enabled for local dev so the Next.js frontend (running on a different
# port) can call this service directly during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    return generate_lineups(req)


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return run_simulation(req)
