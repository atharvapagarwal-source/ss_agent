"""
Webhook router — receives real-time platform events (comments, DMs)
and queues them for Agent 4 processing.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import structlog
from fastapi import APIRouter, Request, Response, HTTPException, Query
from sqlalchemy import text

from config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Meta Webhook (Instagram + Facebook comments) ──────────────────────────────

@router.get("/meta")
async def meta_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/meta")
async def meta_webhook_handler(request: Request):
    """Receive and queue Meta comment/mention events."""
    body = await request.body()

    # Verify webhook signature
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    await _process_meta_webhook(payload)
    return {"status": "ok"}


async def _process_meta_webhook(payload: dict):
    """Parse Meta webhook payload and dispatch comment events to Agent 4."""
    from workers.tasks.dm_dispatcher import dispatch_dm_task
    from agents.agent4_dm_automator import process_comment_event

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "comments":
                # Build normalized event
                platform = "instagram" if "instagram" in str(entry.get("id", "")) else "facebook"
                comment_data = value.get("item", {})

                # Lookup tenant from platform page ID
                tenant_id = await _resolve_tenant_by_page(entry.get("id"))
                if not tenant_id:
                    continue

                # Lookup post by platform post ID
                post_id = await _resolve_post_by_native_id(
                    native_id=value.get("post_id", ""),
                    platform=platform
                )

                event = {
                    "tenant_id": tenant_id,
                    "post_id": post_id,
                    "platform": platform,
                    "comment_id": value.get("comment_id", ""),
                    "commenter_user_id": value.get("sender_id", ""),
                    "commenter_username": value.get("from", {}).get("name", ""),
                    "commenter_display_name": value.get("from", {}).get("name", ""),
                    "comment_text": value.get("message", ""),
                    "comment_posted_at": value.get("created_time"),
                    "platform_post_id": value.get("post_id", ""),
                }

                # Log raw event to webhook_event_log
                await _log_webhook_event(tenant_id, platform, "comment", event)

                # Process via Agent 4
                import asyncio
                asyncio.create_task(process_comment_event(event))


# ── LinkedIn Webhook ──────────────────────────────────────────────────────────

@router.post("/linkedin")
async def linkedin_webhook_handler(request: Request):
    """LinkedIn comment events (via LinkedIn Events API)."""
    payload = await request.json()
    logger.info("LinkedIn webhook received", event_type=payload.get("eventType"))
    # LinkedIn webhook processing — similar pattern to Meta
    return {"status": "ok"}


# ── Twitter/X Webhook ─────────────────────────────────────────────────────────

@router.get("/twitter")
async def twitter_crc_check(crc_token: str = Query()):
    """Twitter webhook CRC (Challenge Response Check)."""
    import base64
    hash_digest = hmac.new(
        settings.TWITTER_API_SECRET.encode(), crc_token.encode(), hashlib.sha256
    ).digest()
    return {"response_token": "sha256=" + base64.b64encode(hash_digest).decode()}


@router.post("/twitter")
async def twitter_webhook_handler(request: Request):
    """Receive Twitter reply/mention events."""
    payload = await request.json()
    # Process tweet replies that match trigger keywords
    for event in payload.get("tweet_create_events", []):
        if not event.get("in_reply_to_status_id"):
            continue
        logger.info("Twitter reply received", tweet_id=event.get("id_str"))
    return {"status": "ok"}


# ── Real-Time Notifications (SSE) ─────────────────────────────────────────────

@router.get("/stream/{tenant_id}")
async def notification_stream(tenant_id: str, request: Request):
    """
    Server-Sent Events stream for real-time push notifications to the coach portal.
    Subscribes to the tenant's Redis Pub/Sub channel.
    """
    import redis.asyncio as aioredis
    from fastapi.responses import StreamingResponse

    async def event_generator():
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"tenant:{tenant_id}:notifications")
        try:
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
        finally:
            await pubsub.unsubscribe()
            await r.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _resolve_tenant_by_page(page_id: str) -> str | None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT tenant_id FROM vault.oauth_tokens WHERE platform_page_id=:pid LIMIT 1"),
            {"pid": str(page_id)},
        )
        row = result.mappings().first()
        return str(row["tenant_id"]) if row else None


async def _resolve_post_by_native_id(native_id: str, platform: str) -> str | None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id FROM posts WHERE platform_post_ids->>:platform = :native_id AND status='PUBLISHED' LIMIT 1"),
            {"platform": platform, "native_id": native_id},
        )
        row = result.mappings().first()
        return str(row["id"]) if row else None


async def _log_webhook_event(tenant_id: str, platform: str, event_type: str, payload: dict) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO webhook_event_log (tenant_id, platform, event_type, raw_payload, processed)
                VALUES (:tid, :platform, :event_type, :payload::jsonb, FALSE)
            """),
            {"tid": tenant_id, "platform": platform, "event_type": event_type, "payload": json.dumps(payload)},
        )
        await session.commit()
