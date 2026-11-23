from fastapi.testclient import TestClient

from app.main import app
from app.worker.seed import build_dataset


def test_healthz():
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_seed_dataset_is_deterministic():
    assert build_dataset("hash") == build_dataset("hash")


def test_seed_dataset_shape():
    data = build_dataset("hash")
    assert len(data["users"]) == 46
    assert len(data["courses"]) == 8
    # unique emails, all on the reserved .test domain
    emails = [u[2] for u in data["users"]]
    assert len(set(emails)) == len(emails)
    assert all(e.endswith("@attendfx.test") for e in emails)
