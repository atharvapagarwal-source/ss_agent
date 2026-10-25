"""
Newsjack poller Celery tasks.
Runs daily trend research and every-15-min newsjack polls for all active tenants.
"""
import asyncio
import structlog
from workers.celery_app import celery_app
from sqlalchemy import text

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120, name="workers.tasks.newsjack_poller.run_daily_trend_research")
def run_daily_trend_research(self):
    """
    Daily: Run full Agent 1 research pipeline for all active tenants
    and trigger Agent 2 content generation.
    """
    asyncio.get_event_loop().run_until_complete(_daily_trend_research_async())


async def _daily_trend_research_async():
    from database import AsyncSessionLocal
    from agents.orchestrator import run_full_pipeline

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id FROM tenants
                WHERE status = 'active'
                  AND feature_newsjack = TRUE
                  OR status = 'trial'
            """)
        )
        tenant_ids = [str(row[0]) for row in result.fetchall()]

    logger.info("Running daily trend research", tenant_count=len(tenant_ids))

    for tenant_id in tenant_ids:
        try:
            await run_full_pipeline(tenant_id=tenant_id, trigger="daily_schedule")
            logger.info("Pipeline started", tenant_id=tenant_id)
        except Exception as exc:
            logger.error("Pipeline failed for tenant", tenant_id=tenant_id, error=str(exc))


@celery_app.task(bind=True, max_retries=2, name="workers.tasks.newsjack_poller.poll_all_tenants_newsjack")
def poll_all_tenants_newsjack(self):
    """Every 15 mins: Check for breaking news relevant to each active tenant."""
    asyncio.get_event_loop().run_until_complete(_newsjack_poll_async())


async def _newsjack_poll_async():
    from database import AsyncSessionLocal
    from agents.agent1_researcher import poll_newsjack_only, _load_brand_profile
    import redis.asyncio as aioredis
    import json
    from config import settings

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT t.id, tbp.coaching_niche, tbp.target_audience, tbp.core_keywords
                FROM tenants t
                JOIN tenant_brand_profiles tbp ON tbp.tenant_id = t.id
                WHERE t.status = 'active' AND t.feature_newsjack = TRUE
            """)
        )
        tenants = [dict(row) for row in result.mappings().all()]

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    for tenant in tenants:
        tenant_id = str(tenant["id"])
        brand_profile = {
            "coaching_niche": tenant["coaching_niche"],
            "target_audience": tenant["target_audience"],
            "core_keywords": tenant["core_keywords"] or [],
        }

        try:
            alerts = await poll_newsjack_only(tenant_id, brand_profile)
            urgent_alerts = [a for a in alerts if a["severity"] == "URGENT"]

            if urgent_alerts:
                # Persist urgent alerts & notify coach immediately
                for alert in urgent_alerts:
                    await _persist_and_notify_urgent(tenant_id, alert, r)

        except Exception as exc:
            logger.error("Newsjack poll failed", tenant_id=tenant_id, error=str(exc))


async def _persist_and_notify_urgent(tenant_id: str, alert: dict, r) -> None:
    """Save urgent newsjack alert to DB and push real-time notification."""
    from database import AsyncSessionLocal
    import uuid
    import json

    async with AsyncSessionLocal() as session:
        alert_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO newsjack_alerts (
                    id, tenant_id, severity, headline, source_url,
                    summary, company_name, event_type,
                    niche_relevance_score, is_actioned
                ) VALUES (
                    :id, :tid, :sev, :headline, :url,
                    :summary, :company, :event_type,
                    :score, FALSE
                )
                ON CONFLICT DO NOTHING
            """),
            {
                "id": alert_id,
                "tid": tenant_id,
                "sev": alert["severity"],
                "headline": alert["headline"],
                "url": alert["source_url"],
                "summary": alert["summary"],
                "company": alert.get("company_name"),
                "event_type": alert.get("event_type", "other"),
                "score": alert.get("relevance_score", 0.8),
            },
        )
        await session.commit()

    # Push to coach's notification channel
    notification = json.dumps({
        "type": "URGENT_NEWSJACK",
        "alert_id": alert_id,
        "headline": alert["headline"],
        "severity": alert["severity"],
        "company": alert.get("company_name"),
    })
    await r.publish(f"tenant:{tenant_id}:notifications", notification)
    await r.lpush(f"tenant:{tenant_id}:urgent_alerts", notification)
    await r.expire(f"tenant:{tenant_id}:urgent_alerts", 86400)
