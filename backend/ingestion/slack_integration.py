"""Slack webhook parsing and posting helpers."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib import error, request

from backend.config import load_local_env


WATCH_TERMS = ("auth", "401", "500")
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


async def receive_slack_event(payload: dict[str, Any]) -> dict[str, str] | None:
    """Parse a Slack event webhook payload.

    Returns ``{text, channel, user, ts}`` for relevant human messages. For the
    demo, relevance means the message contains ``auth``, ``401``, or ``500``.
    """
    event = payload.get("event")
    if not isinstance(event, dict):
        return None

    if event.get("type") != "message":
        return None
    if event.get("subtype") in {"bot_message", "message_deleted", "message_changed"}:
        return None
    if event.get("bot_id"):
        return None

    text = event.get("text")
    channel = event.get("channel")
    user = event.get("user")
    ts = event.get("ts")
    if not all(isinstance(value, str) and value for value in (text, channel, user, ts)):
        return None

    lowered = text.lower()
    if not any(term in lowered for term in WATCH_TERMS):
        return None

    return {"text": text, "channel": channel, "user": user, "ts": ts}


async def post_slack_message(channel: str, text: str) -> bool:
    """Post a message to Slack using ``SLACK_BOT_TOKEN``.

    Returns ``True`` only when Slack accepts the message.
    """
    if not channel.strip():
        raise ValueError("channel must not be empty")
    if not text.strip():
        raise ValueError("text must not be empty")

    load_local_env()
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return False

    return await asyncio.to_thread(_post_slack_message_sync, token, channel, text)


def verify_slack_signature(headers: dict[str, str], body: bytes) -> bool:
    """Verify Slack's request signature when ``SLACK_SIGNING_SECRET`` is set."""
    load_local_env()
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    if not signing_secret:
        return True

    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not timestamp.isdigit() or not signature.startswith("v0="):
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    base = b"v0:" + timestamp.encode("utf-8") + b":" + body
    expected = "v0=" + hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _post_slack_message_sync(token: str, channel: str, text: str) -> bool:
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = request.Request(
        SLACK_POST_MESSAGE_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "aubi-demo",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            return bool(body.get("ok"))
    except (error.HTTPError, error.URLError, json.JSONDecodeError):
        return False
