"""S3 upload and presigned download URLs."""

from __future__ import annotations

import os

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

PRESIGN_EXPIRES = 600  # 10 minutes

_session_kwargs = {}
if os.getenv("AWS_ACCESS_KEY") and os.getenv("AWS_SECRET_KEY"):
    _session_kwargs = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_KEY"),
    }

_region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-2"))
s3 = boto3.client(
    "s3",
    region_name=_region,
    endpoint_url=f"https://s3.{_region}.amazonaws.com",
    config=Config(signature_version="s3v4"),
    **_session_kwargs,
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "qrify-web-platform-storage-prod")


def upload_png(file_buffer, s3_key: str) -> None:
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=file_buffer,
        ContentType="image/png",
    )


def delete_object(s3_key: str) -> None:
    s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)


def presign_get(s3_key: str, expires_in: int = PRESIGN_EXPIRES) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires_in,
    )
