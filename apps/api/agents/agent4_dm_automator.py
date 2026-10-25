"""
Agent 4: Comment-to-DM Lead Magnet & Funnel Automation Agent.

Responsibilities:
  - Listen to real-time comment webhooks across all platforms.
  - Fuzzy-match comments against each post's configured trigger keywords.
  - Post a natural, non-repetitive public reply to boost engagement.
  - Queue and send personalized DMs with anti-spam jitter delays.
  - Log every captured lead to the CRM with full attribution.
  - Respect per-tenant, per-platform rate limits set by SuperAdmin.
"""
from __future__ import annotations
import asyncio
import json
import random
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from thefuzz import fuzz
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import text

from config import settings
from agents.state import AgentState

logger = structlog.get_logger(__name__)

llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.8,
)

# Fuzzy match threshold (0-100). 70 = "RESUME" matches "resume", "RÉSUMÉ", "resuem"
FUZZY_THRESHOLD = 70

PUBLIC_REPLY_SYSTEM = """You are a friendly, human-sounding social media community manager 
for a career coach. Write a SHORT public reply (max 2 sentences) confirming you've sent 
a DM to the commenter. Be warm, natural, and vary your phrasing each time. 
Never sound robotic or copy-paste. Use their name if provided.
Reply in the same language as the original comment.
Return ONLY the reply text, nothing else."""


# ── Core Comment Processing (called by webhook worker) ────────────────────────

async def process_comment_event(event: dict) -> Optional[dict]:
    """
    Entry point called by BullMQ/Celery webhook worker for each comment event.

    event = {
        "tenant_id": "uuid",
        "post_id": "uuid",
        "platform": "instagram",
        "comment_id": "12345",
        "commenter_user_id": "67890",
        "commenter_username": "john_doe",
        "commenter_display_name": "John Doe",
        "comment_text": "RESUME please!",
        "comment_posted_at": "2024-01-15T10:30:00Z",
        "platform_post_id": "native_post_id",
    }
    """
    tenant_id = event["tenant_id"]
    platform = event["platform"]
    comment_text = event.get("comment_text", "")
    log = logger.bind(agent="agent4", tenant_id=tenant_id, platform=platform)

    # ── Step 1: Dedup check ───────────────────────────────────────────────────
    if await _is_duplicate_comment(tenant_id, platform, event["comment_id"]):
        log.debug("Duplicate comment, skipping", comment_id=event["comment_id"])
        return None

    # ── Step 2: Load post's configured trigger keywords ───────────────────────
    post_config = await _load_post_dm_config(event["post_id"], tenant_id, platform)
    if not post_config:
        log.debug("No DM config for post", post_id=event["post_id"])
        return None

    trigger_keyword = post_config.get("keyword", "")
    lead_magnet_id = post_config.get("lead_magnet_id")

    # ── Step 3: Fuzzy keyword match ───────────────────────────────────────────
    match_score = _fuzzy_match(comment_text, trigger_keyword)
    if match_score < FUZZY_THRESHOLD:
        log.debug(
            "Comment does not match trigger",
            comment=comment_text[:50],
            keyword=trigger_keyword,
            score=match_score,
        )
        return None

    log.info(
        "Trigger keyword matched!",
        keyword=trigger_keyword,
        score=match_score,
        commenter=event.get("commenter_username"),
    )

    # ── Step 4: Rate limit check ──────────────────────────────────────────────
    if not await _check_rate_limit(tenant_id, platform):
        log.warning("Rate limit exceeded, requeing for later", tenant_id=tenant_id)
        await _requeue_for_later(event, tenant_id, platform)
        return None

    # ── Step 5: Create lead CRM record ───────────────────────────────────────
    lead_id = await _create_lead_record(event, trigger_keyword, lead_magnet_id)

    # ── Step 6: Post natural public reply (async, non-blocking) ──────────────
    asyncio.create_task(
        _post_public_reply(event, trigger_keyword, lead_id)
    )

    # ── Step 7: Compute jitter delay & queue DM ───────────────────────────────
    rate_config = await _load_rate_config(tenant_id, platform)
    jitter_seconds = random.uniform(
        rate_config["min_jitter_ms"] / 1000,
        rate_config["max_jitter_ms"] / 1000,
    )
    scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=jitter_seconds)

    dm_automation_id = await _enqueue_dm(
        lead_id=lead_id,
        tenant_id=tenant_id,
        platform=platform,
        lead_magnet_id=lead_magnet_id,
        commenter=event,
        scheduled_at=scheduled_at,
    )

    log.info(
        "DM queued with jitter",
        lead_id=lead_id,
        dm_id=dm_automation_id,
        delay_s=round(jitter_seconds),
        scheduled_at=scheduled_at.isoformat(),
    )

    return {
        "lead_id": lead_id,
        "dm_automation_id": dm_automation_id,
        "scheduled_at": scheduled_at.isoformat(),
        "matched_keyword": trigger_keyword,
        "match_score": match_score,
    }


# ── DM Dispatch (called by Celery worker at scheduled time) ───────────────────

async def dispatch_dm(dm_automation_id: str) -> dict:
    """
    Actually sends the DM. Called by the Celery worker after the jitter delay.
    Handles platform-specific DM APIs and updates lead CRM status.
    """
    from database import AsyncSessionLocal
    from services.platform import meta_service, linkedin_service, twitter_service

    async with AsyncSessionLocal() as session:
        # Load DM queue record
        result = await session.execute(
            text("""
                SELECT da.*, cl.platform_user_id, cl.platform_username,
                       cl.platform_display_name, cl.lead_magnet_id, cl.tenant_id,
                       lm.dm_message_template, lm.delivery_url
                FROM dm_automations da
                JOIN captured_leads cl ON cl.id = da.lead_id
                LEFT JOIN lead_magnets lm ON lm.id = cl.lead_magnet_id
                WHERE da.id = :id AND da.status = 'queued'
            """),
            {"id": dm_automation_id},
        )
        record = result.mappings().first()

    if not record:
        return {"status": "skipped", "reason": "not_found_or_already_sent"}

    tenant_id = record["tenant_id"]
    platform = record["platform"]
    log = logger.bind(dm_id=dm_automation_id, platform=platform, tenant_id=tenant_id)

    # Build personalized DM message
    dm_message = _build_dm_message(
        template=record.get("dm_message_template", "Hey {name}! Here's your resource: {url}"),
        display_name=record.get("platform_display_name", "there"),
        delivery_url=record.get("delivery_url", ""),
    )

    # Get decrypted OAuth token
    from services.oauth_vault import get_decrypted_token
    token = await get_decrypted_token(tenant_id, platform)

    try:
        # Platform-specific DM dispatch
        platform_dm_id = None
        if platform in ("instagram", "facebook"):
            platform_dm_id = await meta_service.send_dm(
                token=token,
                recipient_id=record["platform_user_id"],
                message=dm_message,
                platform=platform,
            )
        elif platform == "linkedin":
            platform_dm_id = await linkedin_service.send_dm(
                token=token,
                recipient_urn=record["platform_user_id"],
                message=dm_message,
            )
        elif platform == "twitter":
            platform_dm_id = await twitter_service.send_dm(
                token=token,
                recipient_id=record["platform_user_id"],
                message=dm_message,
            )

        # Update DM status to sent
        await _update_dm_status(dm_automation_id, record["lead_id"], "sent", platform_dm_id)
        log.info("DM sent successfully", dm_message_id=platform_dm_id)
        return {"status": "sent", "dm_id": platform_dm_id}

    except Exception as exc:
        log.error("DM dispatch failed", error=str(exc))
        await _update_dm_status(dm_automation_id, record["lead_id"], "failed", error=str(exc))

        # Retry logic
        await _increment_attempt(dm_automation_id)
        return {"status": "failed", "error": str(exc)}


# ── Public Reply Generator ────────────────────────────────────────────────────

async def _post_public_reply(event: dict, trigger_keyword: str, lead_id: str) -> None:
    """Generate and post a natural public reply to boost engagement."""
    platform = event["platform"]
    commenter_name = event.get("commenter_display_name") or event.get("commenter_username", "")

    try:
        response = await llm.ainvoke([
            SystemMessage(content=PUBLIC_REPLY_SYSTEM),
            HumanMessage(content=(
                f"Commenter name: {commenter_name}\n"
                f"Original comment: {event['comment_text']}\n"
                f"Trigger keyword they used: {trigger_keyword}\n"
                f"Platform: {platform}"
            )),
        ])
        reply_text = response.content.strip()

        from services.oauth_vault import get_decrypted_token
        token = await get_decrypted_token(event["tenant_id"], platform)

        reply_id = None
        if platform in ("instagram", "facebook"):
            from services.platform import meta_service
            reply_id = await meta_service.post_comment_reply(
                token=token,
                comment_id=event["comment_id"],
                reply_text=reply_text,
                platform=platform,
            )
        elif platform == "twitter":
            from services.platform import twitter_service
            reply_id = await twitter_service.reply_to_tweet(
                token=token,
                tweet_id=event["comment_id"],
                reply_text=reply_text,
            )
        elif platform == "linkedin":
            from services.platform import linkedin_service
            reply_id = await linkedin_service.post_comment_reply(
                token=token,
                comment_urn=event["comment_id"],
                reply_text=reply_text,
            )

        # Update lead record with public reply status
        if reply_id:
            await _mark_public_reply_sent(lead_id, reply_id)

        logger.info("Public reply posted", platform=platform, reply_id=reply_id)

    except Exception as exc:
        logger.warning("Public reply failed (non-critical)", error=str(exc))


# ── Fuzzy Matching ────────────────────────────────────────────────────────────

def _fuzzy_match(comment_text: str, trigger_keyword: str) -> int:
    """
    Check if comment contains the trigger keyword using multiple fuzzy strategies.
    Returns match score 0-100.
    """
    comment_upper = comment_text.upper().strip()
    keyword_upper = trigger_keyword.upper().strip()

    # Exact substring match (fastest path)
    if keyword_upper in comment_upper:
        return 100

    # Word-by-word token check
    words = comment_upper.split()
    for word in words:
        score = fuzz.ratio(word, keyword_upper)
        if score >= FUZZY_THRESHOLD:
            return score

    # Full comment partial ratio (catches multi-word triggers)
    return fuzz.partial_ratio(keyword_upper, comment_upper)


# ── Rate Limiting ─────────────────────────────────────────────────────────────

async def _check_rate_limit(tenant_id: str, platform: str) -> bool:
    """Returns True if DM is allowed, False if rate limit exceeded."""
    from database import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    hour_key = f"{tenant_id}:{platform}:{now.strftime('%Y-%m-%d:%H')}"
    day_key = f"{tenant_id}:{platform}:{now.strftime('%Y-%m-%d')}"

    async with AsyncSessionLocal() as session:
        # Load rate limit config
        config_result = await session.execute(
            text("""
                SELECT hourly_limit, daily_limit FROM dm_rate_limit_config
                WHERE (tenant_id = :tid OR tenant_id IS NULL)
                  AND platform = :platform
                ORDER BY tenant_id NULLS LAST
                LIMIT 1
            """),
            {"tid": tenant_id, "platform": platform},
        )
        config_row = config_result.mappings().first()
        hourly_limit = config_row["hourly_limit"] if config_row else 20
        daily_limit = config_row["daily_limit"] if config_row else 100

        # Count sent DMs in current hour window
        hour_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM dm_automations
                WHERE tenant_id = :tid AND platform = :platform
                  AND rate_window_key = :hour_key
                  AND status = 'sent'
            """),
            {"tid": tenant_id, "platform": platform, "hour_key": hour_key},
        )
        hourly_count = hour_result.scalar()

        # Count sent DMs today
        day_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM dm_automations
                WHERE tenant_id = :tid AND platform = :platform
                  AND rate_window_key LIKE :day_key
                  AND status = 'sent'
            """),
            {"tid": tenant_id, "platform": platform, "day_key": f"{day_key}%"},
        )
        daily_count = day_result.scalar()

    return hourly_count < hourly_limit and daily_count < daily_limit


# ── Database Helpers ──────────────────────────────────────────────────────────

async def _is_duplicate_comment(tenant_id: str, platform: str, comment_id: str) -> bool:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT 1 FROM captured_leads WHERE tenant_id=:tid AND platform=:pl AND comment_id=:cid"),
            {"tid": tenant_id, "pl": platform, "cid": comment_id},
        )
        return result.scalar() is not None


async def _load_post_dm_config(post_id: str, tenant_id: str, platform: str) -> Optional[dict]:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT dm_trigger_keywords->:platform AS config
                FROM posts WHERE id = :pid AND tenant_id = :tid AND status = 'PUBLISHED'
            """),
            {"platform": platform, "pid": post_id, "tid": tenant_id},
        )
        row = result.mappings().first()
        if row and row["config"]:
            return json.loads(row["config"]) if isinstance(row["config"], str) else row["config"]
    return None


async def _load_rate_config(tenant_id: str, platform: str) -> dict:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT min_jitter_ms, max_jitter_ms FROM dm_rate_limit_config
                WHERE (tenant_id = :tid OR tenant_id IS NULL) AND platform = :platform
                ORDER BY tenant_id NULLS LAST LIMIT 1
            """),
            {"tid": tenant_id, "platform": platform},
        )
        row = result.mappings().first()
        return dict(row) if row else {"min_jitter_ms": 30000, "max_jitter_ms": 300000}


async def _create_lead_record(event: dict, trigger_keyword: str, lead_magnet_id: Optional[str]) -> str:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        lead_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO captured_leads (
                    id, tenant_id, post_id, lead_magnet_id,
                    platform, platform_user_id, platform_username, platform_display_name,
                    trigger_keyword, original_comment_text, comment_id, comment_posted_at,
                    dm_status, source
                ) VALUES (
                    :id, :tenant_id, :post_id, :magnet_id,
                    :platform, :user_id, :username, :display_name,
                    :keyword, :comment, :comment_id, :comment_at,
                    'queued', 'comment_trigger'
                )
            """),
            {
                "id": lead_id,
                "tenant_id": event["tenant_id"],
                "post_id": event.get("post_id"),
                "magnet_id": lead_magnet_id,
                "platform": event["platform"],
                "user_id": event["commenter_user_id"],
                "username": event["commenter_username"],
                "display_name": event.get("commenter_display_name"),
                "keyword": trigger_keyword,
                "comment": event["comment_text"],
                "comment_id": event["comment_id"],
                "comment_at": event.get("comment_posted_at"),
            },
        )
        await session.commit()
    return lead_id


async def _enqueue_dm(
    lead_id: str,
    tenant_id: str,
    platform: str,
    lead_magnet_id: Optional[str],
    commenter: dict,
    scheduled_at: datetime,
) -> str:
    from database import AsyncSessionLocal
    now = datetime.now(timezone.utc)
    window_key = f"{tenant_id}:{platform}:{now.strftime('%Y-%m-%d:%H')}"

    async with AsyncSessionLocal() as session:
        dm_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO dm_automations (
                    id, tenant_id, lead_id, platform,
                    priority, scheduled_at, status, rate_window_key
                ) VALUES (
                    :id, :tenant_id, :lead_id, :platform,
                    5, :scheduled_at, 'queued', :window_key
                )
            """),
            {
                "id": dm_id,
                "tenant_id": tenant_id,
                "lead_id": lead_id,
                "platform": platform,
                "scheduled_at": scheduled_at,
                "window_key": window_key,
            },
        )
        await session.commit()

    # Also push to Celery for time-based execution
    from workers.tasks.dm_dispatcher import dispatch_dm_task
    eta_seconds = (scheduled_at - datetime.now(timezone.utc)).total_seconds()
    dispatch_dm_task.apply_async(args=[dm_id], countdown=max(1, int(eta_seconds)))

    return dm_id


async def _update_dm_status(
    dm_id: str, lead_id: str, status: str,
    dm_message_id: Optional[str] = None, error: Optional[str] = None
) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE dm_automations SET status = :status, last_attempt_at = NOW(),
                    attempts = attempts + 1 WHERE id = :id
            """),
            {"status": status, "id": dm_id},
        )
        sent_at = "NOW()" if status == "sent" else "NULL"
        await session.execute(
            text(f"""
                UPDATE captured_leads SET
                    dm_status = :status,
                    dm_sent_at = {sent_at if status == 'sent' else 'dm_sent_at'},
                    dm_id = COALESCE(:dm_msg_id, dm_id),
                    dm_error_message = :error
                WHERE id = :lead_id
            """),
            {"status": status, "dm_msg_id": dm_message_id, "error": error, "lead_id": lead_id},
        )
        await session.commit()


async def _increment_attempt(dm_id: str) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE dm_automations SET attempts = attempts + 1 WHERE id = :id"),
            {"id": dm_id},
        )
        await session.commit()


async def _mark_public_reply_sent(lead_id: str, reply_id: str) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE captured_leads SET public_reply_posted=TRUE, public_reply_id=:rid WHERE id=:lid"),
            {"rid": reply_id, "lid": lead_id},
        )
        await session.commit()


async def _requeue_for_later(event: dict, tenant_id: str, platform: str) -> None:
    """If rate limited, push back to Redis queue for processing in 1 hour."""
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await r.lpush(f"dm_backlog:{tenant_id}:{platform}", json.dumps(event))
    await r.expire(f"dm_backlog:{tenant_id}:{platform}", 7200)


def _build_dm_message(template: str, display_name: str, delivery_url: str) -> str:
    first_name = display_name.split()[0] if display_name else "there"
    return (
        template
        .replace("{name}", first_name)
        .replace("{url}", delivery_url)
        .replace("{display_name}", display_name)
    )
