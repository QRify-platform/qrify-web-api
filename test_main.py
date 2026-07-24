"""
Unit tests — no real Postgres or S3.
We stub the DB lifecycle and the service's I/O adapters.
Auth is overridden (no real Cognito JWT).
"""

from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from auth.cognito import get_current_user
from main import app

FAKE_USER = {"sub": "user-sub-1", "email": "test@example.com", "username": "test"}
FAKE_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "source_url": "http://example.com/",
    "s3_key": "qr_codes/11111111-1111-1111-1111-111111111111.png",
    "user_id": "user-sub-1",
    "created_at": "2026-07-18T12:00:00+00:00",
}
FAKE_URL = "https://s3.example.com/presigned"


@contextmanager
def _client():
    # Keep patches active for the whole TestClient lifespan (startup + requests).
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    try:
        with patch("main.init_db"), patch("main.close_db"):
            with TestClient(app) as client:
                yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


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
    assert mock_insert.call_args.kwargs["user_id"] == "user-sub-1"
    mock_presign.assert_called_once_with(FAKE_ROW["s3_key"])


@patch("services.qr_service.presign_get", return_value=FAKE_URL)
@patch("services.qr_service.upload_png")
@patch("services.qr_service.qr_repo.insert_qr_code", return_value=FAKE_ROW)
def test_generate_qr_is_preview_only(mock_insert, mock_upload, mock_presign):
    """Generate returns a data URL and does not persist."""
    with _client() as client:
        response = client.post("/generate-qr/", params={"url": "http://example.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["source_url"].startswith("http://example.com")
    assert body["qr_code_url"].startswith("data:image/png;base64,")
    mock_upload.assert_not_called()
    mock_insert.assert_not_called()
    mock_presign.assert_not_called()


def test_generate_qr_no_auth_required():
    with patch("main.init_db"), patch("main.close_db"):
        with TestClient(app) as client:
            response = client.post("/generate-qr/", params={"url": "http://example.com"})
    assert response.status_code == 200
    assert response.json()["qr_code_url"].startswith("data:image/png;base64,")


def test_create_qr_invalid_url():
    with _client() as client:
        response = client.post("/qr-codes", json={"url": ""})

    assert response.status_code == 422


def test_create_requires_auth():
    with patch("main.init_db"), patch("main.close_db"):
        with TestClient(app) as client:
            response = client.post("/qr-codes", json={"url": "http://example.com"})
    assert response.status_code == 401


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


@patch("services.qr_service.presign_get", return_value=FAKE_URL)
@patch(
    "services.qr_service.qr_repo.list_qr_codes_for_user",
    return_value=[FAKE_ROW],
)
def test_list_my_qr_codes(mock_list, mock_presign):
    with _client() as client:
        response = client.get("/qr-codes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == FAKE_ROW["id"]
    mock_list.assert_called_once_with("user-sub-1")


@patch("services.qr_service.delete_object")
@patch("services.qr_service.qr_repo.delete_qr_code_for_user", return_value=FAKE_ROW)
@patch("services.qr_service.qr_repo.get_qr_code_by_id", return_value=FAKE_ROW)
def test_delete_qr_code(mock_get, mock_delete_row, mock_delete_s3):
    with _client() as client:
        response = client.delete(f"/qr-codes/{FAKE_ROW['id']}")

    assert response.status_code == 204
    mock_delete_row.assert_called_once()
    mock_delete_s3.assert_called_once_with(FAKE_ROW["s3_key"])


@patch("services.qr_service.qr_repo.get_qr_code_by_id", return_value=None)
def test_delete_qr_not_found(mock_get):
    with _client() as client:
        response = client.delete(f"/qr-codes/{FAKE_ROW['id']}")

    assert response.status_code == 404


@patch(
    "services.qr_service.qr_repo.get_qr_code_by_id",
    return_value={**FAKE_ROW, "user_id": "someone-else"},
)
def test_delete_qr_forbidden(mock_get):
    with _client() as client:
        response = client.delete(f"/qr-codes/{FAKE_ROW['id']}")

    assert response.status_code == 403


def test_health():
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
