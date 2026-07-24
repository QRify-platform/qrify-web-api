"""
Unit tests — no real Postgres or S3.
We stub the DB lifecycle and the service's I/O adapters.
"""

from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

FAKE_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "source_url": "http://example.com/",
    "s3_key": "qr_codes/11111111-1111-1111-1111-111111111111.png",
    "created_at": "2026-07-18T12:00:00+00:00",
}
FAKE_URL = "https://s3.example.com/presigned"


@contextmanager
def _client():
    # Keep patches active for the whole TestClient lifespan (startup + requests).
    with patch("main.init_db"), patch("main.close_db"):
        with TestClient(app) as client:
            yield client


@patch("services.qr_service.presign_get", return_value=FAKE_URL)
@patch("services.qr_service.upload_png")
@patch("services.qr_service.qr_repo.insert_qr_code", return_value=FAKE_ROW)
def test_create_qr_codes(mock_insert, mock_upload, mock_presign):
    with _client() as client:
        response = client.post("/qr-codes", json={"url": "http://example.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == FAKE_ROW["id"]
    assert body["download_url"] == FAKE_URL
    assert body["qr_code_url"] == FAKE_URL
    assert body["expires_in"] == 600
    mock_upload.assert_called_once()
    mock_insert.assert_called_once()
    mock_presign.assert_called_once_with(FAKE_ROW["s3_key"])


@patch("services.qr_service.presign_get", return_value=FAKE_URL)
@patch("services.qr_service.upload_png")
@patch("services.qr_service.qr_repo.insert_qr_code", return_value=FAKE_ROW)
def test_generate_qr_compat(mock_insert, mock_upload, mock_presign):
    """Old web UI still posts to /generate-qr/?url=..."""
    with _client() as client:
        response = client.post("/generate-qr/", params={"url": "http://example.com"})

    assert response.status_code == 200
    assert response.json()["qr_code_url"] == FAKE_URL


def test_create_qr_invalid_url():
    with _client() as client:
        response = client.post("/qr-codes", json={"url": "not-a-url"})

    assert response.status_code == 422


@patch("services.qr_service.presign_get", return_value=FAKE_URL)
@patch("services.qr_service.qr_repo.get_qr_code_by_id", return_value=FAKE_ROW)
def test_get_qr_by_id(mock_get, mock_presign):
    with _client() as client:
        response = client.get(f"/qr-codes/{FAKE_ROW['id']}")

    assert response.status_code == 200
    assert response.json()["download_url"] == FAKE_URL
    mock_get.assert_called_once()
    mock_presign.assert_called_once_with(FAKE_ROW["s3_key"])


@patch("services.qr_service.qr_repo.get_qr_code_by_id", return_value=None)
def test_get_qr_not_found(mock_get):
    with _client() as client:
        response = client.get("/qr-codes/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 404


def test_get_qr_bad_id():
    with _client() as client:
        response = client.get("/qr-codes/not-a-uuid")

    assert response.status_code == 400


def test_health():
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
