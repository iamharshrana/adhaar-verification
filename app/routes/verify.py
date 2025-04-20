from fastapi import APIRouter, UploadFile, HTTPException
from app.services.aadhaar import verify_aadhaar

router = APIRouter()

@router.post("/verify-aadhaar")
async def verify_aadhaar_route(file: UploadFile):
    content_type = file.content_type
    if content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    file_bytes = await file.read()
    result = verify_aadhaar(file_bytes, content_type)
    return result