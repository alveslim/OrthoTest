import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.api import router

load_dotenv()

app = FastAPI(
    title="OrthoTest API",
    version="1.1.0",
    description="API acadêmica para registro de avaliações ortopédicas.",
)

origins = [
    item.strip()
    for item in os.getenv("CORS_ORIGINS", "http://localhost:8550,http://127.0.0.1:8550").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # o requests do navegador manda cabeçalhos extras (User-Agent...); sem cookies, então é seguro
)

app.include_router(router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "orthotest-api"}
