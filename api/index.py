"""
Vercel serverless entry point for the AI Tech News Engine API.

Vercel's Python runtime imports a module-level ASGI/WSGI app named `app`.
The existing application code lives under `backend/app/...` and uses absolute
imports like `from app.routes.chat import ...`, so we add `backend/` to
sys.path before importing the FastAPI app.
"""
import os
import sys

# Make `backend/` importable so `import app.*` resolves.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app  # noqa: E402  (import after sys.path tweak)

# Expose `app` for Vercel's Python runtime.
__all__ = ["app"]
