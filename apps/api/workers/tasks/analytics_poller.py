"""Analytics poller Celery tasks — high-frequency telemetry + daily rollups."""
import asyncio
import structlog
from workers.celery_app import celery_app
from sqlalchemy import text

logger = structlog.get_logger(__name__)


@celery_app.task(name="workers.tasks.analytics_poller.poll_telemetry_task")
def poll_telemetry_task(post_id: str, tenant_id: str):
    """Triggered immediately after publish and then via beat schedule."""
    asyncio.get_event_loop().run_until_complete(_poll_single(post_id, tenant_id))


async def _poll_single(post_id: str, tenant_id: str):
    from agents.agent5_analytics import poll_post_telemetry
    await poll_post_telemetry(post_id=post_id, tenant_id=tenant_id)


@celery_app.task(name="workers.tasks.analytics_poller.poll_all_active_posts")
def poll_all_active_posts():
    """Every 60s: Poll telemetry for all posts in HF polling sets."""
    asyncio.get_event_loop().run_until_complete(_poll_all_async())


async def _poll_all_async():
    import redis.asyncio as aioredis
    from config import settings
    from agents.agent5_analytics import poll_post_telemetry
    from database import AsyncSessionLocal

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Get all tenant IDs with active HF polling sets
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id FROM tenants WHERE status = 'active'")
        )
        tenant_ids = [str(row[0]) for row in result.fetchall()]

    tasks = []
    for tenant_id in tenant_ids:
        post_ids = await r.smembers(f"tenant:{tenant_id}:hf_polling")
        for post_id in post_ids:
            tasks.append(poll_post_telemetry(post_id=post_id, tenant_id=tenant_id))

    if tasks:
        import asyncio
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("HF telemetry poll complete", posts_polled=len(tasks))


@celery_app.task(name="workers.tasks.analytics_poller.compute_daily_rollup")
def compute_daily_rollup():
    """Daily: Aggregate telemetry into daily_analytics_rollup table."""
    asyncio.get_event_loop().run_until_complete(_rollup_async())


async def _rollup_async():
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            INSERT INTO daily_analytics_rollup (
                tenant_id, date, platform,
                total_posts, total_impressions, total_reach,
                total_engagement, avg_engagement_rate, total_leads, computed_at
            )
            SELECT
                p.tenant_id,
                CURRENT_DATE - INTERVAL '1 day' as date,
                pas.platform,
                COUNT(DISTINCT p.id) as total_posts,
                SUM(pas.total_impressions) as total_impressions,
                SUM(pas.total_reach) as total_reach,
                SUM(pas.total_likes + pas.total_comments + pas.total_shares) as total_engagement,
                AVG(
                    CASE WHEN pas.total_reach > 0
                    THEN (pas.total_likes + pas.total_comments + pas.total_shares)::float / pas.total_reach
                    ELSE 0 END
                ) as avg_engagement_rate,
                SUM(pas.total_leads_captured) as total_leads,
                NOW() as computed_at
            FROM post_analytics_summary pas
            JOIN posts p ON p.id = pas.post_id
            WHERE p.published_at::date = CURRENT_DATE - INTERVAL '1 day'
            GROUP BY p.tenant_id, pas.platform
            ON CONFLICT (tenant_id, date, platform) DO UPDATE SET
                total_posts = EXCLUDED.total_posts,
                total_impressions = EXCLUDED.total_impressions,
                total_reach = EXCLUDED.total_reach,
                total_engagement = EXCLUDED.total_engagement,
                avg_engagement_rate = EXCLUDED.avg_engagement_rate,
                total_leads = EXCLUDED.total_leads,
                computed_at = NOW()
        """))
        await session.commit()
    logger.info("Daily analytics rollup complete")
