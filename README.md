# QRify Web API

**QRify Web API** is the backend service for the QRify platform. It provides a FastAPI-powered endpoint to generate QR codes from user-submitted URLs and store them in an AWS S3 bucket.

---
## 🚀 Features

- 🔗 Accepts a **URL** via API and generates a PNG QR Code
- ☁️ Uploads the QR code to **Amazon S3**
- 🌍 Returns a **publicly accessible URL** to the QR code (via presigned S3 link)
- 🌐 Supports **CORS** for local frontend development
- 🩺 **Health check** endpoint at `/health` for monitoring readiness
- 📊 **Prometheus metrics** exposed at `/metrics` for observability and scraping
- 🧪 Lightweight, fast, and cloud-ready — perfect for serverless, containers, or Kubernetes
---

## ⚙️ Tech Stack
| Technology   | Description                                      |
|--------------|--------------------------------------------------|
| FastAPI      | Python async web framework                       |
| Uvicorn      | ASGI server to run FastAPI                       |
| qrcode       | Python QR code generation library                |
| Boto3        | AWS SDK for Python (used for S3 uploads)         |
| python-dotenv| Loads environment variables from `.env`          |
| Prometheus   | Monitoring tool, scrapes metrics from API        |
| Instrumentator | Exposes FastAPI metrics in Prometheus format  |
| CORS         | Cross-Origin Resource Sharing (frontend support) |

---

## 📦 Setup

### ✅ Prerequisites

- Python 3.9+
- AWS Account with:
  - S3 Bucket created
  - Programmatic access enabled

---

### 📁 Clone and Install

```bash
cd qrify-web-api
pip install -r requirements.txt
