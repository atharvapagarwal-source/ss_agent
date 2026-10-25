"""Scheduler tasks — publish queued posts and monthly quota resets."""
import asyncio
import structlog
from workers.celery_app import celery_app
from sqlalchemy import text

logger = structlog.get_logger(__name__)


@celery_app.task(name="workers.tasks.scheduler.enqueue_publish")
async def enqueue_publish(post_id: str, tenant_id: str, scheduled_at=None):
    """Queue a post for publishing (now or at scheduled_at)."""
    from workers.tasks.scheduler import execute_publish_task
    if scheduled_at:
        from datetime import datetime, timezone
        import pytz
        eta = datetime.fromisoformat(scheduled_at)
        execute_publish_task.apply_async(args=[post_id, tenant_id], eta=eta)
    else:
        execute_publish_task.apply_async(args=[post_id, tenant_id], countdown=1)


@celery_app.task(bind=True, max_retries=3, name="workers.tasks.scheduler.execute_publish_task")
def execute_publish_task(self, post_id: str, tenant_id: str):
    asyncio.get_event_loop().run_until_complete(_execute_publish(post_id, tenant_id))


async def _execute_publish(post_id: str, tenant_id: str):
    """Resume the LangGraph graph at the publisher_node for an approved post."""
    from database import AsyncSessionLocal
    from agents.orchestrator import get_graph

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT run_id FROM posts WHERE id=:id"), {"id": post_id}
        )
        # run_id stored in a future migration; for now use post_id as thread_id
        pass

    graph = get_graph()
    config = {"configurable": {"thread_id": post_id}}
    await graph.ainvoke(None, config=config)
    logger.info("Publish executed via scheduler", post_id=post_id)


@celery_app.task(name="workers.tasks.scheduler.reset_monthly_quotas")
def reset_monthly_quotas():
    asyncio.get_event_loop().run_until_complete(_reset_quotas())


async def _reset_quotas():
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            UPDATE tenants SET
                posts_used_this_month = 0,
                dms_used_this_month = 0,
                quota_reset_at = date_trunc('month', NOW()) + INTERVAL '1 month'
            WHERE quota_reset_at <= NOW()
        """))
        await session.commit()
    logger.info("Monthly quotas reset")
