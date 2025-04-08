
#backend/route

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.qrcode.qservice import QRService
from fastapi import Form

router = APIRouter()
qr_service = QRService()

class QRRequest(BaseModel):
    content: str
    size: int = 10

@router.post("/generate")
def generate_qr(
    content: str = Form(...),
    size: int = Form(10)
):
    try:
        # Validate and generate SVG
        svg = qr_service.create_qr(content, size)
        
        # Return JSON response with SVG
        return {
            "svg": svg,
            "content": content,
            "size": size
        }
    except ValueError as ve:
        # Handle specific validation errors
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Catch-all for other unexpected errors
        raise HTTPException(status_code=500, detail="Internal Server Error")