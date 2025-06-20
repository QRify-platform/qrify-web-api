import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

BUCKET_NAME = 'qrify-platform-storage'

def upload_to_s3(file_buffer, file_name) -> dict:
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_name,
        Body=file_buffer,
        ContentType='image/png'
    )
    s3_url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': file_name},
        ExpiresIn=600
    )
    return {"qr_code_url": s3_url}
