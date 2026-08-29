from fastapi.testclient import TestClient

from dfs_ev.api import app

from .conftest import SAMPLE_DK_CSV

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_optimize_endpoint_returns_salary_legal_lineups():
    resp = client.post("/optimize", json={"csv_path": SAMPLE_DK_CSV, "lineups": 2})
    assert resp.status_code == 200
    lineups = resp.json()
    assert len(lineups) == 2
    for lu in lineups:
        assert len(lu["players"]) == 6
        assert lu["total_salary"] <= 50_000


def test_optimize_endpoint_rejects_bad_csv_path():
    resp = client.post("/optimize", json={"csv_path": "no/such/file.csv"})
    assert resp.status_code == 400
