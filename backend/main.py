"""FastAPI entrypoint for the AUBI demo backend."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from backend.ingestion.slack_integration import (
    post_slack_message,
    receive_slack_event,
    verify_slack_signature,
)


app = FastAPI(title="AUBI Demo")
logger = logging.getLogger(__name__)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/slack/webhook")
async def slack_webhook(request: Request) -> dict[str, Any]:
    raw_body = await request.body()
    if not verify_slack_signature(dict(request.headers), raw_body):
        raise HTTPException(status_code=401, detail="invalid Slack signature")

    payload = await request.json()

    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    event = await receive_slack_event(payload)
    if event:
        asyncio.create_task(run_graph_for_slack(event))

    return {"ok": True}


async def run_graph_for_slack(event: dict[str, str]) -> None:
    """Trigger the AUBI graph for a Slack incident.

    This placeholder preserves the integration boundary for the demo. When the
    full graph runner is available, call it here and post its resolution.
    """
    logger.info("Received Slack incident trigger: %s", event)
    await post_slack_message(
        event["channel"],
        "AUBI received the incident and is investigating the authentication failure.",
    )
