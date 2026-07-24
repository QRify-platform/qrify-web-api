# QRify Web API

Backend for QRify: generate QR PNGs, store them in private S3, and keep durable metadata in Postgres.

## How it fits together (interview cheat sheet)

```
Client → FastAPI routes (api/routes.py)
       → service (services/qr_service.py)     # business flow
       → db/qr_codes.py                       # INSERT / SELECT
       → utils/s3_utils.py                    # put_object + presign GET
```

| Concern | Where | Why |
|---------|--------|-----|
| PNG bytes | S3 key `qr_codes/{uuid}.png` | Object storage |
| id ↔ s3_key | Postgres `qr_codes` | Durable lookup after presign expires |
| Download URL | Generated on each create/get | Short-lived (~10 min), never stored |

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/qr-codes` | JSON `{"url":"..."}` → `201` + `id` + `download_url` |
| `GET` | `/qr-codes/{id}` | Fresh presign from stored `s3_key` |
| `POST` | `/generate-qr/?url=...` | Compat for current Next.js UI |
| `GET` | `/health` | Liveness |

## Env

| Variable | Source |
|----------|--------|
| `DATABASE_URL` | Secrets Manager → ESO → `qrify-web-api-db` |
| `S3_BUCKET_NAME` | Chart / env |
| `AWS_REGION` | Chart / env (IRSA in cluster; no static keys) |

## Local

```bash
cd qrify-web-api
pip install -r requirements.txt httpx==0.27.2 pytest
export DATABASE_URL=postgresql://...   # needed at startup
PYTHONPATH=. pytest test_main.py -v    # unit tests mock DB/S3
```

Tech: FastAPI, Uvicorn, qrcode, boto3, psycopg, Prometheus instrumentator.
