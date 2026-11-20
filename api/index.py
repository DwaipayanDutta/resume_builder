"""Vercel entry point: serves the Resume Studio FastAPI app as a Python function.

Every /api/* request is routed here by vercel.json; the web UI (web/dist) is served as
static files by Vercel itself.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from resume_builder.api.main import app  # noqa: E402,F401  (Vercel looks for `app`)
