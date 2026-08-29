from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from dk_ev.api.main import app, get_db
from dk_ev.models import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = TestSessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


SMALL_PAYLOAD = {
    "sport": "nfl",
    "contest_type": "gpp",
    "num_lineups": 3,
    "max_overlap": 6,
    "n_iterations": 500,
    "field_sample_size": 50,
    "field_size": 1000,
    "random_seed": 7,
}


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_optimize_returns_ranked_lineups(client: TestClient):
    resp = client.post("/optimize", json=SMALL_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] >= 1
    assert body["sport"] == "nfl"
    assert len(body["lineups"]) == 3
    evs = [lu["ev"] for lu in body["lineups"]]
    assert evs == sorted(evs, reverse=True)
    for lu in body["lineups"]:
        assert lu["salary"] <= 50_000
        assert len(lu["roster"]) == 9


def test_get_lineups_by_run_id(client: TestClient):
    created = client.post("/optimize", json=SMALL_PAYLOAD).json()
    run_id = created["run_id"]
    resp = client.get(f"/lineups/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id


def test_get_lineups_404_for_unknown_run(client: TestClient):
    resp = client.get("/lineups/99999")
    assert resp.status_code == 404


def test_export_csv_matches_dk_format(client: TestClient):
    created = client.post("/optimize", json=SMALL_PAYLOAD).json()
    run_id = created["run_id"]
    resp = client.get(f"/export/csv/{run_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0] == "QB,RB,RB,WR,WR,WR,TE,FLEX,DST"
    assert len(lines) == 1 + created["lineups"].__len__()


def test_list_runs(client: TestClient):
    client.post("/optimize", json=SMALL_PAYLOAD)
    resp = client.get("/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert runs[0]["num_lineups"] == 3


def test_invalid_sport_returns_400(client: TestClient):
    payload = dict(SMALL_PAYLOAD, sport="curling")
    resp = client.post("/optimize", json=payload)
    assert resp.status_code == 400
