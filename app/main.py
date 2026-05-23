"""FastAPI main entry point"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ocr

app = FastAPI(
    title="Zeta Banco Onboarding OCR API",
    description="KYC automatizado con OCR para cedula paraguaya. Procesa imagen, extrae datos, valida autenticidad.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router, prefix="/api", tags=["OCR"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "onboarding-ocr"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
