from fastapi import FastAPI
from backend.routers.api import router

app = FastAPI(title="OrthoTest API", version="1.0.0")

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}