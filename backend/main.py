"""Minimal GitHub-only API for the AUBI demo repository."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from backend.config import load_local_env
from backend.ingestion.github_issue import get_latest_open_issue


app = FastAPI(title="AUBI Demo GitHub API")


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/github/poll")
async def poll_github() -> dict[str, Any]:
    """Return the latest open issue on ``DEMO_REPO`` for the frontend poller."""
    load_local_env()
    demo_repo = os.getenv("DEMO_REPO", "").strip()
    if not demo_repo:
        return {"issue": None}

    return {"issue": get_latest_open_issue(demo_repo)}
