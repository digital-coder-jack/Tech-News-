"""
Vercel serverless entry point for the AI Tech News Engine backend.

Vercel's Python runtime imports an ASGI application named ``app`` from the
files under the ``api/`` directory. The FastAPI app lives in
``backend/app/main.py`` and uses absolute imports rooted at ``app`` (e.g.
``from app.routes.news import ...``), so we add ``backend/`` to ``sys.path``
before importing it.

All HTTP routes are routed here via ``vercel.json`` so the same code that runs
on Railway also runs on Vercel without modification.
"""

import os
import sys

# Make the backend package importable: backend/app/... -> import app.*
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Re-export the FastAPI ASGI app for Vercel's Python runtime to serve.
from app.main import app  # noqa: E402

# Vercel detects the module-level ``app`` (ASGI) automatically.
__all__ = ["app"]
