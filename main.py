from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter
import qrcode
import boto3
import os
from io import BytesIO
import re
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for frontend dev (update origin in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← Replace with frontend domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint
Instrumentator().instrument(app).expose(app)

# AWS S3 setup
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)
bucket_name = 'qrify-platform-storage'

@app.post("/generate-qr/")
async def generate_qr(url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    def sanitize_filename(url: str):
        return "qr_codes/" + re.sub(r'[^\w\-_.]', '_', url) + ".png"

    file_name = sanitize_filename(url)

    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=img_byte_arr,
            ContentType='image/png'
        )
        s3_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket_name, 'Key': file_name},
            ExpiresIn=600
        )
        return {"qr_code_url": s3_url}
    except Exception:
        print("UPLOAD FAILED:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail="QR code generation failed")
