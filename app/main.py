from fastapi import FastAPI
from app.routes import verify

app = FastAPI(title="Aadhaar Verification API")

app.include_router(verify.router, prefix="/aadhaar", tags=["Aadhaar Verification"])
