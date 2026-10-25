"""
Agent 3: Human-in-the-Loop (HITL) Gatekeeper.

This agent NEVER publishes automatically.
It manages the state machine transitions, persists drafts to DB,
sends real-time push notifications to the coach, and only transitions
to APPROVED / PUBLISHED when an explicit human action is recorded.

State machine:
  DRAFTING → AWAITING_HUMAN_APPROVAL (or URGENT_NEWSJACK_APPROVAL)
           → REVISION_REQUESTED → [back to Agent 2]
           → APPROVED → SCHEDULED | PUBLISHED
"""
from __future__ import annotations
import json
import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.state import AgentState, HITLRevision
from config import settings
import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

# Redis client for real-time push notifications
_redis: Optional[aioredis.Redis] = None


def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            return None
    return _redis


# ── Core Node: Persist draft & notify coach ───────────────────────────────────

async def agent3_hitl_gatekeeper(state: AgentState) -> dict:
    """
    LangGraph node: Persist post to DB and emit push notification.
    The actual approval/rejection comes via the FastAPI HITL router
    (human action from the portal), not from this node.
    """
    tenant_id = state["tenant_id"]
    log = logger.bind(agent="agent3_hitl", tenant_id=tenant_id)
    log.info("Agent 3 activated", status=state.get("post_status"))

    try:
        status = state.get("post_status", "AWAITING_HUMAN_APPROVAL")
        post_id = state.get("post_id")

        # ── Step 1: Persist / update post in DB ──────────────────────────────
        if not post_id:
            post_id = await _create_post_in_db(state)
            log.info("Post created in DB", post_id=post_id)
        else:
            await _update_post_in_db(state, post_id)
            log.info("Post updated in DB", post_id=post_id)

        # ── Step 2: Save revision record if this is a re-draft ───────────────
        if state.get("human_feedback") is None and len(state.get("hitl_revisions", [])) > 0:
            # A revision cycle just completed — record it
            revision = state["hitl_revisions"][-1]
            await _persist_revision(post_id, state["tenant_id"], revision)

        # ── Step 3: Send real-time push notification to coach ─────────────────
        await _push_approval_notification(tenant_id, post_id, state)

        log.info("Agent 3 complete — awaiting human action", post_id=post_id)

        return {
            "post_id": post_id,
            "post_status": status,
            "current_agent": "agent3_hitl",  # Stay here until human acts
        }

    except Exception as exc:
        log.error("Agent 3 failed", error=str(exc))
        return {
            "errors": [f"agent3_hitl_gatekeeper: {exc}"],
            "post_status": "AWAITING_HUMAN_APPROVAL",
        }


# ── Human Action Handlers (called from FastAPI HITL router) ──────────────────

async def handle_approval(
    post_id: str,
    tenant_id: str,
    user_id: str,
    schedule_at: Optional[str],
    run_id: str,
) -> dict:
    """
    Called when a coach clicks 'Approve & Publish' or 'Approve & Schedule'.
    Updates DB status, then triggers the publish pipeline via Celery.
    """
    log = logger.bind(action="approve", post_id=post_id, tenant_id=tenant_id)

    new_status = "SCHEDULED" if schedule_at else "APPROVED"
    await _update_post_status(
        post_id=post_id,
        tenant_id=tenant_id,
        new_status=new_status,
        user_id=user_id,
        scheduled_at=schedule_at,
    )

    # Enqueue publish task
    from workers.tasks.scheduler import enqueue_publish
    await enqueue_publish(post_id=post_id, tenant_id=tenant_id, scheduled_at=schedule_at)

    log.info("Post approved", new_status=new_status)
    return {"post_id": post_id, "status": new_status}


async def handle_revision_request(
    post_id: str,
    tenant_id: str,
    user_id: str,
    feedback: str,
    run_id: str,
    graph,  # LangGraph CompiledStateGraph instance
) -> dict:
    """
    Called when coach submits a natural language revision prompt.
    Resumes the LangGraph pipeline, routing back to Agent 2.
    """
    log = logger.bind(action="revision", post_id=post_id, feedback=feedback[:80])

    # Load current state
    config = {"configurable": {"thread_id": run_id}}
    current_state = await graph.aget_state(config)
    current_values = current_state.values

    # Record revision snapshot
    revision: HITLRevision = {
        "revision_number": len(current_values.get("hitl_revisions", [])) + 1,
        "human_feedback": feedback,
        "snapshot_before": current_values.get("platform_content", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Update DB
    await _update_post_status(
        post_id=post_id,
        tenant_id=tenant_id,
        new_status="REVISION_REQUESTED",
        user_id=user_id,
    )

    # Resume LangGraph graph at agent2_creator with new feedback
    update = {
        "human_feedback": feedback,
        "post_status": "REVISION_REQUESTED",
        "hitl_revisions": [revision],
        "current_agent": "agent2_creator",
    }
    await graph.aupdate_state(config, update, as_node="agent3_hitl_gatekeeper")

    # Resume execution from agent2
    await graph.ainvoke(None, config=config)

    log.info("Revision routed to Agent 2", revision_num=revision["revision_number"])
    return {"post_id": post_id, "status": "REVISION_REQUESTED", "revision": revision}


# ── DB Helpers ────────────────────────────────────────────────────────────────

async def _create_post_in_db(state: AgentState) -> str:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        post_id = str(uuid.uuid4())
        platform_content = state.get("platform_content", {})
        dm_keywords = _build_dm_keywords_from_content(platform_content)

        await session.execute(
            text("""
                INSERT INTO posts (
                    id, tenant_id, trend_report_id, newsjack_alert_id,
                    title, status, is_urgent_newsjack,
                    platform_content, dm_trigger_keywords,
                    platforms_to_publish, agent_model_used, generation_tokens
                ) VALUES (
                    :id, :tenant_id, NULL, NULL,
                    :title, :status, :urgent,
                    :content::jsonb, :dm_keywords::jsonb,
                    :platforms, :model, :tokens
                )
            """),
            {
                "id": post_id,
                "tenant_id": state["tenant_id"],
                "title": state.get("post_title", "Untitled Post"),
                "status": state.get("post_status", "AWAITING_HUMAN_APPROVAL"),
                "urgent": state.get("is_urgent_newsjack", False),
                "content": json.dumps(state.get("platform_content", {})),
                "dm_keywords": json.dumps(dm_keywords),
                "platforms": state.get("platforms_to_publish", []),
                "model": settings.GEMINI_PRO_MODEL,
                "tokens": state.get("tokens_used", 0),
            },
        )
        await session.commit()
        return post_id


async def _update_post_in_db(state: AgentState, post_id: str) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        platform_content = state.get("platform_content", {})
        dm_keywords = _build_dm_keywords_from_content(platform_content)
        await session.execute(
            text("""
                UPDATE posts SET
                    title = :title,
                    status = :status,
                    platform_content = :content::jsonb,
                    dm_trigger_keywords = :dm_keywords::jsonb,
                    revision_count = revision_count + 1,
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {
                "title": state.get("post_title", "Untitled Post"),
                "status": state.get("post_status"),
                "content": json.dumps(platform_content),
                "dm_keywords": json.dumps(dm_keywords),
                "id": post_id,
                "tenant_id": state["tenant_id"],
            },
        )
        await session.commit()


async def _persist_revision(post_id: str, tenant_id: str, revision: HITLRevision) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO hitl_revisions (
                    post_id, tenant_id, revision_number,
                    from_status, to_status,
                    human_feedback, snapshot_before, actioned_at
                ) VALUES (
                    :post_id, :tenant_id, :rev_num,
                    'AWAITING_HUMAN_APPROVAL', 'REVISION_REQUESTED',
                    :feedback, :snapshot::jsonb, NOW()
                )
            """),
            {
                "post_id": post_id,
                "tenant_id": tenant_id,
                "rev_num": revision["revision_number"],
                "feedback": revision["human_feedback"],
                "snapshot": json.dumps(revision["snapshot_before"]),
            },
        )
        await session.commit()


async def _update_post_status(
    post_id: str,
    tenant_id: str,
    new_status: str,
    user_id: str,
    scheduled_at: Optional[str] = None,
) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        params: dict = {
            "status": new_status,
            "id": post_id,
            "tenant_id": tenant_id,
            "scheduled_at": scheduled_at,
        }
        await session.execute(
            text("""
                UPDATE posts SET
                    status = :status,
                    scheduled_publish_at = :scheduled_at,
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            params,
        )
        await session.commit()


# ── Real-Time Push Notification via Redis Pub/Sub ─────────────────────────────

async def _push_approval_notification(
    tenant_id: str, post_id: str, state: AgentState
) -> None:
    """
    Publish a notification to the tenant's Redis channel.
    The Next.js frontend subscribes via SSE or WebSocket to receive this.
    """
    is_urgent = state.get("is_urgent_newsjack", False)
    channel = f"tenant:{tenant_id}:notifications"
    payload = json.dumps({
        "type": "HITL_APPROVAL_REQUIRED",
        "post_id": post_id,
        "post_title": state.get("post_title", "New Post"),
        "is_urgent": is_urgent,
        "status": state.get("post_status"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    try:
        r = get_redis()
        if r:
            await r.publish(channel, payload)
            if is_urgent:
                # Also push to urgent queue (displayed as banner alert in portal)
                await r.lpush(f"tenant:{tenant_id}:urgent_alerts", payload)
                await r.expire(f"tenant:{tenant_id}:urgent_alerts", 86400)
    except Exception as e:
        logger.debug("Redis notification skipped", error=str(e))


# ── Utilities ─────────────────────────────────────────────────────────────────

def _build_dm_keywords_from_content(platform_content: dict) -> dict:
    """Extract per-platform CTA keywords into the dm_trigger_keywords structure."""
    mapping = {
        "instagram": "instagram_cta_keyword",
        "linkedin": "linkedin_cta_keyword",
        "twitter": "twitter_cta_keyword",
        "facebook": "facebook_cta_keyword",
    }
    result = {}
    for platform, key in mapping.items():
        if keyword := platform_content.get(key):
            result[platform] = {"keyword": keyword, "lead_magnet_id": None}
    return result
