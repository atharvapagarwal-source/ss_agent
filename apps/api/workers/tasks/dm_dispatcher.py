"""DM dispatcher Celery tasks — execute queued DMs and retry backlog."""
import asyncio
import structlog
from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300, name="workers.tasks.dm_dispatcher.dispatch_dm_task")
def dispatch_dm_task(self, dm_automation_id: str):
    """Execute a single queued DM dispatch."""
    try:
        result = asyncio.get_event_loop().run_until_complete(
            _dispatch_async(dm_automation_id)
        )
        if result.get("status") == "failed":
            raise Exception(result.get("error", "DM dispatch failed"))
        return result
    except Exception as exc:
        logger.error("DM task failed", dm_id=dm_automation_id, error=str(exc))
        raise self.retry(exc=exc)


async def _dispatch_async(dm_automation_id: str) -> dict:
    from agents.agent4_dm_automator import dispatch_dm
    return await dispatch_dm(dm_automation_id)


@celery_app.task(name="workers.tasks.dm_dispatcher.retry_backlog_dms")
def retry_backlog_dms():
    """Every 5 mins: Re-attempt DMs that were rate-limited and stored in Redis backlog."""
    asyncio.get_event_loop().run_until_complete(_retry_backlog_async())


async def _retry_backlog_async():
    import redis.asyncio as aioredis
    import json
    from config import settings
    from agents.agent4_dm_automator import process_comment_event

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Scan for all backlog keys
    async for key in r.scan_iter("dm_backlog:*"):
        event_json = await r.rpop(key)
        if event_json:
            try:
                event = json.loads(event_json)
                await process_comment_event(event)
            except Exception as exc:
                logger.warning("Backlog DM retry failed", error=str(exc))
                # Put back at end of list
                await r.lpush(key, event_json)
