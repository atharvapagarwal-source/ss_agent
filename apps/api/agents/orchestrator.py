"""
LangGraph Multi-Agent Orchestrator.

Defines the stateful graph connecting all 5 agents with conditional edges
implementing the HITL state machine. Uses Redis-backed checkpointing for
fault-tolerant, resumable workflows.

Graph topology:
  START → agent1_researcher
        → agent2_creator
        → agent3_hitl_gatekeeper  (INTERRUPT — waits for human)
        → [APPROVED] → publisher
        → [REVISION_REQUESTED] → agent2_creator (loop)

Agent 4 & 5 are activated as separate Celery tasks post-publish.
"""
from __future__ import annotations
import uuid
import structlog
from typing import Any, Literal

from langgraph.graph import StateGraph, START, END

try:
    from langgraph.checkpoint.memory import MemorySaver
except Exception:
    MemorySaver = None

from agents.state import AgentState
from agents.agent1_researcher import agent1_researcher
from agents.agent2_creator import agent2_creator
from agents.agent3_hitl import agent3_hitl_gatekeeper
from config import settings

logger = structlog.get_logger(__name__)


# ── Publisher Node ─────────────────────────────────────────────────────────────

async def publisher_node(state: AgentState) -> dict:
    """
    Publishes approved content to selected platforms.
    Only reached after explicit human approval (APPROVED status).
    """
    from services.platform import meta_service, linkedin_service, twitter_service
    from services.oauth_vault import get_decrypted_token
    from database import AsyncSessionLocal
    from sqlalchemy import text
    import json

    tenant_id = state["tenant_id"]
    post_id = state["post_id"]
    content = state.get("platform_content", {})
    platforms = state.get("platforms_to_publish", [])

    log = logger.bind(node="publisher", post_id=post_id, tenant_id=tenant_id)
    log.info("Publishing approved post", platforms=platforms)

    platform_post_ids: dict = {}
    errors: list[str] = []

    for platform in platforms:
        try:
            token = await get_decrypted_token(tenant_id, platform)

            if platform == "linkedin":
                result = await linkedin_service.publish_post(
                    token=token,
                    text_post=content.get("linkedin_text_post", ""),
                    pdf_url=content.get("linkedin_carousel_pdf_url"),
                )
                platform_post_ids["linkedin"] = result.get("id")

            elif platform == "instagram":
                result = await meta_service.publish_instagram(
                    token=token,
                    caption=content.get("instagram_caption", ""),
                    carousel_urls=content.get("instagram_carousel_png_urls", []),
                )
                platform_post_ids["instagram"] = result.get("id")

            elif platform == "facebook":
                result = await meta_service.publish_facebook(
                    token=token,
                    post_text=content.get("facebook_post", ""),
                )
                platform_post_ids["facebook"] = result.get("id")

            elif platform == "twitter":
                result = await twitter_service.publish_thread(
                    token=token,
                    tweets=content.get("twitter_thread", []),
                )
                platform_post_ids["twitter"] = result.get("id")

            log.info("Published to platform", platform=platform, native_id=platform_post_ids.get(platform))

        except Exception as exc:
            err_msg = f"publish:{platform}:{exc}"
            log.error("Publish failed", platform=platform, error=str(exc))
            errors.append(err_msg)

    # Update DB with published status and platform post IDs
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE posts SET
                    status = 'PUBLISHED',
                    published_at = NOW(),
                    platform_post_ids = :ids::jsonb,
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tid
            """),
            {
                "ids": json.dumps(platform_post_ids),
                "id": post_id,
                "tid": tenant_id,
            },
        )
        # Update monthly quota usage
        await session.execute(
            text("UPDATE tenants SET posts_used_this_month = posts_used_this_month + 1 WHERE id = :tid"),
            {"tid": tenant_id},
        )
        await session.commit()

    # Activate Agent 4 (comment listener) & Agent 5 (analytics) via Celery
    if platform_post_ids:
        await _activate_post_publish_workers(post_id, tenant_id, platform_post_ids)

    log.info("Publish complete", platform_post_ids=platform_post_ids)

    return {
        "post_status": "PUBLISHED",
        "current_agent": "completed",
        "errors": errors,
    }


async def _activate_post_publish_workers(
    post_id: str, tenant_id: str, platform_post_ids: dict
) -> None:
    """Start Agent 4 webhook subscription and Agent 5 high-frequency polling."""
    import redis.asyncio as aioredis
    import json

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Add post to high-frequency polling set (Agent 5)
    await r.sadd(f"tenant:{tenant_id}:hf_polling", post_id)

    # Register webhook subscriptions for each platform (Agent 4)
    for platform, native_id in platform_post_ids.items():
        await r.hset(
            f"post_meta:{post_id}",
            mapping={
                f"{platform}_native_id": native_id,
                "tenant_id": tenant_id,
            },
        )

    # Trigger initial telemetry poll immediately
    from workers.tasks.analytics_poller import poll_telemetry_task
    poll_telemetry_task.apply_async(args=[post_id, tenant_id], countdown=60)

    logger.info("Post-publish workers activated", post_id=post_id, tenant_id=tenant_id)


# ── Routing Functions ─────────────────────────────────────────────────────────

def route_after_hitl(state: AgentState) -> Literal["agent2_creator", "publisher_node", "__end__"]:
    """
    Conditional edge from agent3_hitl_gatekeeper.
    Returns next node based on human action (set via API, not agent).
    """
    status = state.get("post_status")
    if status == "REVISION_REQUESTED":
        return "agent2_creator"
    elif status in ("APPROVED", "SCHEDULED"):
        return "publisher_node"
    else:
        # Still waiting for human action — graph suspends at INTERRUPT
        return "__end__"


def route_after_agent2(state: AgentState) -> Literal["agent3_hitl_gatekeeper"]:
    """Agent 2 always routes to HITL gatekeeper."""
    return "agent3_hitl_gatekeeper"


# ── Graph Construction ────────────────────────────────────────────────────────

def build_graph() -> Any:
    """
    Construct and compile the LangGraph stateful workflow.
    Uses Redis checkpointer for persistence between human interactions.
    """
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("agent1_researcher", agent1_researcher)
    graph.add_node("agent2_creator", agent2_creator)
    graph.add_node("agent3_hitl_gatekeeper", agent3_hitl_gatekeeper)
    graph.add_node("publisher_node", publisher_node)

    # Define edges
    graph.add_edge(START, "agent1_researcher")
    graph.add_edge("agent1_researcher", "agent2_creator")
    graph.add_edge("agent2_creator", "agent3_hitl_gatekeeper")

    # HITL node has a conditional edge (awaits human approval)
    graph.add_conditional_edges(
        "agent3_hitl_gatekeeper",
        route_after_hitl,
        {
            "agent2_creator": "agent2_creator",   # Revision loop
            "publisher_node": "publisher_node",   # Approved → publish
            "__end__": END,                        # Waiting for human
        },
    )
    graph.add_edge("publisher_node", END)

    # Compile with MemorySaver (or optional Redis if available)
    checkpointer = None
    try:
        if settings.REDIS_URL and "localhost" not in settings.REDIS_URL:
            from langgraph.checkpoint.redis import RedisSaver
            checkpointer = RedisSaver.from_conn_string(settings.REDIS_URL)
    except Exception:
        pass

    if checkpointer is None and MemorySaver is not None:
        try:
            checkpointer = MemorySaver()
        except Exception:
            checkpointer = None

    compile_kwargs = {"interrupt_before": ["publisher_node"]}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    logger.info("LangGraph compiled successfully")
    return compiled


# ── Singleton graph instance ──────────────────────────────────────────────────
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Public API ────────────────────────────────────────────────────────────────

async def run_full_pipeline(tenant_id: str, trigger: str = "scheduled") -> dict:
    """
    Launch a full Agent 1 → 2 → 3 pipeline run for a tenant.
    Returns the run_id for tracking.
    """
    run_id = str(uuid.uuid4())
    graph = get_graph()

    initial_state: AgentState = {
        "tenant_id": tenant_id,
        "run_id": run_id,
        "trending_topics": [],
        "newsjack_alerts": [],
        "active_newsjack": None,
        "seo_keywords": [],
        "research_sources": [],
        "is_urgent_newsjack": False,
        "post_title": "",
        "platform_content": {},
        "suggested_cta_keyword": "GUIDE",
        "lead_magnet_id": None,
        "platforms_to_publish": [],
        "post_status": "DRAFTING",
        "hitl_revisions": [],
        "human_feedback": None,
        "post_id": None,
        "captured_leads": [],
        "telemetry_snapshots": [],
        "performance_score": None,
        "errors": [],
        "current_agent": "agent1_researcher",
        "tokens_used": 0,
    }

    config = {"configurable": {"thread_id": run_id}}

    logger.info("Starting pipeline", tenant_id=tenant_id, run_id=run_id, trigger=trigger)

    # Run until INTERRUPT (HITL gate) — graph suspends, human must approve
    await graph.ainvoke(initial_state, config=config)

    return {"run_id": run_id, "tenant_id": tenant_id, "status": "awaiting_approval"}


async def resume_after_approval(run_id: str, tenant_id: str) -> dict:
    """
    Resume the graph after human approval.
    The state must already have post_status = 'APPROVED' before calling this.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}
    result = await graph.ainvoke(None, config=config)
    return {"run_id": run_id, "status": "published", "result": result}
