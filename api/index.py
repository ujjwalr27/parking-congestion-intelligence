"""Vercel serverless entrypoint.

Vercel's Python runtime serves the module-level ``app`` (an ASGI app). We simply add the
``backend`` directory to the import path and re-export the existing FastAPI app, so the same
code runs locally (`uvicorn app.main:app`) and on Vercel with no duplication.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402  (import after sys.path tweak)

__all__ = ["app"]
