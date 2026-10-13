"""API and static frontend smoke tests."""
import pytest
from fastapi.testclient import TestClient
from agents.api import app

client = TestClient(app)


def test_normalize_endpoint():
    response = client.post("/api/normalize", json={
        "counts": [100, 200], "lengths_bp": [1000, 2000]
    })
    assert response.status_code == 200
    result = response.json()
    assert result["tpm"] == pytest.approx([500000, 500000])
    assert result["fpkm"] == pytest.approx([1e9 * .1 / 300] * 2)


def test_invalid_counts_return_422():
    response = client.post("/api/normalize", json={
        "counts": [-1, 2], "lengths_bp": [1000, 1000]
    })
    assert response.status_code == 422


def test_static_frontend_and_assets():
    html = client.get("/")
    assert html.status_code == 200
    assert "TPM / FPKM" in html.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/styles.css").status_code == 200
