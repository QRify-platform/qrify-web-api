import os

import boto3
from dotenv import load_dotenv

load_dotenv()

# Prefer IRSA / default credential chain. Explicit keys only for local .env use.
_session_kwargs = {}
if os.getenv("AWS_ACCESS_KEY") and os.getenv("AWS_SECRET_KEY"):
    _session_kwargs = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_KEY"),
    }

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-2")),
    **_session_kwargs,
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "qrify-web-platform-storage")


def upload_to_s3(file_buffer, file_name) -> dict:
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_name,
        Body=file_buffer,
        ContentType="image/png",
    )
    s3_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": file_name},
        ExpiresIn=600,
    )
    return {"qr_code_url": s3_url}
