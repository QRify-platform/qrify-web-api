# QRify Web API

**QRify Web API** is the backend service for the QRify platform. It provides a FastAPI-powered endpoint to generate QR codes from user-submitted URLs and store them in an AWS S3 bucket.

---

## 🚀 Features

- 🔗 Accepts a URL via API and generates a PNG QR Code
- ☁️ Uploads the QR code to **Amazon S3**
- 🌍 Returns a **publicly accessible URL** to the QR code
- 🤝 Supports **CORS** for local frontend development
- 🧪 Lightweight, fast, and cloud-ready

---

## ⚙️ Tech Stack

| Technology | Description                     |
|------------|---------------------------------|
| FastAPI    | Python async web framework      |
| qrcode     | Python QR code generation lib   |
| Boto3      | AWS SDK for Python (S3 uploads) |
| dotenv     | Loads environment secrets       |
| CORS       | Enabled for frontend access     |

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
