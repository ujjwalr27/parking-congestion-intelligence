"""FastAPI app entrypoint.

    uvicorn app.main:app --reload      # from the backend/ directory
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

app = FastAPI(title="Parking Congestion Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # dev: allow the Vite dev server on any port
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "api": "/api/meta"}
