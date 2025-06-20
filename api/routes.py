from fastapi import APIRouter, HTTPException
from services.qr_service import generate_qr_code

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/generate-qr/")
async def generate_qr(url: str):
    try:
        return generate_qr_code(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail="QR code generation failed")