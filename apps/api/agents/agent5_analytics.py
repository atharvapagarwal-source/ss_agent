"""
Agent 5: Real-Time Telemetry & Second-Level Graphical Analytics Engine.

Responsibilities:
  - Poll platform APIs at high frequency (every 60s) for newly published posts.
  - Compute Reach Velocity (impressions & reach gained per second/minute).
  - Capture second-by-second video/Reel retention curves.
  - Track Carousel Swipe-Through Rate per slide.
  - Aggregate cross-platform metrics into post_analytics_summary.
  - Feed top-performing content signals back to Agent 1 & Agent 2.
  - Populate daily_analytics_rollup for dashboard charts.
"""
from __future__ import annotations
import asyncio
import json
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from agents.state import AgentState, TelemetrySnapshot

logger = structlog.get_logger(__name__)


# ── Core Telemetry Poll (called by Celery beat every 60 seconds) ──────────────

async def poll_post_telemetry(post_id: str, tenant_id: str) -> list[TelemetrySnapshot]:
    """
    Main telemetry collection function. Polls all platforms the post was published to
    and writes second-level snapshots to telemetry_timeseries table.
    """
    log = logger.bind(agent="agent5", post_id=post_id, tenant_id=tenant_id)

    snapshots: list[TelemetrySnapshot] = []

    # Load post metadata
    post = await _load_post(post_id, tenant_id)
    if not post:
        log.warning("Post not found for telemetry", post_id=post_id)
        return []

    published_at = post.get("published_at")
    if not published_at:
        return []

    if isinstance(published_at, str):
        published_at = datetime.fromisoformat(published_at)

    now = datetime.now(timezone.utc)
    seconds_since_publish = int((now - published_at).total_seconds())
    platform_post_ids: dict = post.get("platform_post_ids") or {}

    log.info(
        "Polling telemetry",
        seconds_since_publish=seconds_since_publish,
        platforms=list(platform_post_ids.keys()),
    )

    # Poll each platform concurrently
    tasks = []
    for platform, native_post_id in platform_post_ids.items():
        if native_post_id:
            tasks.append(_poll_platform(
                platform=platform,
                native_post_id=native_post_id,
                post_id=post_id,
                tenant_id=tenant_id,
                seconds_since_publish=seconds_since_publish,
            ))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            log.error("Platform poll failed", error=str(result))
        elif result:
            snapshots.append(result)
            await _persist_snapshot(result)

    # Update aggregated summary
    if snapshots:
        await _update_analytics_summary(post_id, tenant_id, snapshots)

    # Check if we should stop high-freq polling (after first hour)
    high_freq_window = int(settings.DATABASE_URL and 3600)  # 1 hour
    if seconds_since_publish > high_freq_window:
        await _stop_high_freq_polling(post_id, tenant_id)
        log.info("Transitioning to low-freq polling", post_id=post_id)

    return snapshots


# ── Platform-Specific Pollers ─────────────────────────────────────────────────

async def _poll_platform(
    platform: str,
    native_post_id: str,
    post_id: str,
    tenant_id: str,
    seconds_since_publish: int,
) -> Optional[TelemetrySnapshot]:
    """Dispatch to the correct platform API poller."""
    from services.oauth_vault import get_decrypted_token

    try:
        token = await get_decrypted_token(tenant_id, platform)

        if platform == "instagram":
            return await _poll_instagram(token, native_post_id, post_id, tenant_id, seconds_since_publish)
        elif platform == "facebook":
            return await _poll_facebook(token, native_post_id, post_id, tenant_id, seconds_since_publish)
        elif platform == "linkedin":
            return await _poll_linkedin(token, native_post_id, post_id, tenant_id, seconds_since_publish)
        elif platform == "twitter":
            return await _poll_twitter(token, native_post_id, post_id, tenant_id, seconds_since_publish)
    except Exception as exc:
        logger.error("Platform poll error", platform=platform, error=str(exc))
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def _poll_instagram(
    token: str, media_id: str, post_id: str, tenant_id: str, seconds_since_publish: int
) -> TelemetrySnapshot:
    from services.platform.meta_service import get_instagram_insights

    data = await get_instagram_insights(token, media_id)
    impressions = data.get("impressions", 0)
    reach = data.get("reach", 0)

    # Get previous snapshot for velocity calculation
    prev = await _get_last_snapshot(post_id, "instagram")
    reach_velocity = _compute_velocity(reach, prev)

    return TelemetrySnapshot(
        post_id=post_id,
        platform="instagram",
        recorded_at=datetime.now(timezone.utc).isoformat(),
        seconds_since_publish=seconds_since_publish,
        impressions=impressions,
        reach=reach,
        reach_velocity=reach_velocity,
        likes=data.get("like_count", 0),
        comments=data.get("comment_count", 0),
        engagement_rate=_compute_engagement_rate(data, reach),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def _poll_facebook(
    token: str, post_id_native: str, post_id: str, tenant_id: str, seconds_since_publish: int
) -> TelemetrySnapshot:
    from services.platform.meta_service import get_facebook_insights

    data = await get_facebook_insights(token, post_id_native)
    reach = data.get("post_impressions_unique", 0)
    impressions = data.get("post_impressions", 0)
    prev = await _get_last_snapshot(post_id, "facebook")

    return TelemetrySnapshot(
        post_id=post_id,
        platform="facebook",
        recorded_at=datetime.now(timezone.utc).isoformat(),
        seconds_since_publish=seconds_since_publish,
        impressions=impressions,
        reach=reach,
        reach_velocity=_compute_velocity(reach, prev),
        likes=data.get("post_reactions_like_total", 0),
        comments=data.get("post_comments", 0),
        engagement_rate=_compute_engagement_rate(data, reach),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def _poll_linkedin(
    token: str, share_urn: str, post_id: str, tenant_id: str, seconds_since_publish: int
) -> TelemetrySnapshot:
    from services.platform.linkedin_service import get_share_statistics

    data = await get_share_statistics(token, share_urn)
    impressions = data.get("impressionCount", 0)
    reach = data.get("uniqueImpressionsCount", 0)
    prev = await _get_last_snapshot(post_id, "linkedin")

    return TelemetrySnapshot(
        post_id=post_id,
        platform="linkedin",
        recorded_at=datetime.now(timezone.utc).isoformat(),
        seconds_since_publish=seconds_since_publish,
        impressions=impressions,
        reach=reach,
        reach_velocity=_compute_velocity(reach, prev),
        likes=data.get("likeCount", 0),
        comments=data.get("commentCount", 0),
        engagement_rate=_compute_engagement_rate(
            {"likes": data.get("likeCount", 0), "comments": data.get("commentCount", 0)},
            reach,
        ),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def _poll_twitter(
    token: str, tweet_id: str, post_id: str, tenant_id: str, seconds_since_publish: int
) -> TelemetrySnapshot:
    from services.platform.twitter_service import get_tweet_metrics

    data = await get_tweet_metrics(token, tweet_id)
    public = data.get("public_metrics", {})
    non_public = data.get("non_public_metrics", {})
    impressions = non_public.get("impression_count", public.get("impression_count", 0))
    reach = impressions  # Twitter doesn't have distinct reach
    prev = await _get_last_snapshot(post_id, "twitter")

    return TelemetrySnapshot(
        post_id=post_id,
        platform="twitter",
        recorded_at=datetime.now(timezone.utc).isoformat(),
        seconds_since_publish=seconds_since_publish,
        impressions=impressions,
        reach=reach,
        reach_velocity=_compute_velocity(reach, prev),
        likes=public.get("like_count", 0),
        comments=public.get("reply_count", 0),
        engagement_rate=_compute_engagement_rate(public, reach),
    )


# ── Performance Score & Feedback Loop ─────────────────────────────────────────

async def compute_performance_score(post_id: str, tenant_id: str) -> float:
    """
    Compute a normalized performance score (0-100) for Agent 1 feedback loop.
    Combines reach velocity, engagement rate, and lead conversion rate.
    """
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    AVG(reach_velocity) as avg_velocity,
                    AVG(engagement_rate) as avg_engagement,
                    SUM(dms_sent)::float / NULLIF(SUM(comments_with_trigger), 0) as dm_conv_rate
                FROM telemetry_timeseries
                WHERE post_id = :pid AND tenant_id = :tid
            """),
            {"pid": post_id, "tid": tenant_id},
        )
        row = result.mappings().first()

    if not row:
        return 0.0

    velocity_score = min(100.0, (row.get("avg_velocity") or 0) * 10)
    engagement_score = min(100.0, (row.get("avg_engagement") or 0) * 500)
    dm_conv_score = min(100.0, (row.get("dm_conv_rate") or 0) * 100)

    # Weighted composite score
    score = (velocity_score * 0.4) + (engagement_score * 0.35) + (dm_conv_score * 0.25)

    # Persist score
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE post_analytics_summary SET performance_score = :score
                WHERE post_id = :pid
            """),
            {"score": round(score, 2), "pid": post_id},
        )
        await session.commit()

    return round(score, 2)


async def build_feedback_for_agent1(tenant_id: str) -> dict:
    """
    Aggregate top-performing content signals to feed back into Agent 1.
    Called periodically to improve future content generation.
    """
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    p.title,
                    p.platform_content->'linkedin'->>'text_post' as li_hook,
                    pas.performance_score,
                    pas.total_leads_captured,
                    pas.dm_conversion_rate,
                    pas.peak_reach_velocity,
                    tr.trending_topics
                FROM post_analytics_summary pas
                JOIN posts p ON p.id = pas.post_id
                LEFT JOIN trend_reports tr ON tr.id = (
                    SELECT id FROM trend_reports
                    WHERE tenant_id = :tid ORDER BY generated_at DESC LIMIT 1
                )
                WHERE pas.tenant_id = :tid
                  AND pas.performance_score IS NOT NULL
                ORDER BY pas.performance_score DESC
                LIMIT 10
            """),
            {"tid": tenant_id},
        )
        top_posts = [dict(r) for r in result.mappings().all()]

    return {
        "top_performing_hooks": [p.get("li_hook", "")[:200] for p in top_posts[:5]],
        "avg_performance_score": sum(p.get("performance_score", 0) for p in top_posts) / max(len(top_posts), 1),
        "best_dm_conversion_rate": max((p.get("dm_conversion_rate") or 0 for p in top_posts), default=0),
        "insight": f"Top {len(top_posts)} posts analyzed for pattern extraction",
    }


# ── DB Helpers ────────────────────────────────────────────────────────────────

async def _persist_snapshot(snapshot: TelemetrySnapshot) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO telemetry_timeseries (
                    tenant_id, post_id, platform,
                    recorded_at, seconds_since_publish,
                    impressions, reach, reach_velocity,
                    likes, comments, engagement_rate
                ) VALUES (
                    (SELECT tenant_id FROM posts WHERE id = :post_id),
                    :post_id, :platform, :recorded_at, :seconds,
                    :impressions, :reach, :velocity,
                    :likes, :comments, :engagement
                )
                ON CONFLICT DO NOTHING
            """),
            {
                "post_id": snapshot["post_id"],
                "platform": snapshot["platform"],
                "recorded_at": snapshot["recorded_at"],
                "seconds": snapshot["seconds_since_publish"],
                "impressions": snapshot["impressions"],
                "reach": snapshot["reach"],
                "velocity": snapshot["reach_velocity"],
                "likes": snapshot["likes"],
                "comments": snapshot["comments"],
                "engagement": snapshot["engagement_rate"],
            },
        )
        await session.commit()


async def _update_analytics_summary(
    post_id: str, tenant_id: str, snapshots: list[TelemetrySnapshot]
) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        for snapshot in snapshots:
            await session.execute(
                text("""
                    INSERT INTO post_analytics_summary (
                        tenant_id, post_id, platform,
                        total_impressions, total_reach, total_likes, total_comments,
                        peak_reach_velocity, peak_velocity_at, last_updated_at
                    ) VALUES (
                        :tenant_id, :post_id, :platform,
                        :impressions, :reach, :likes, :comments,
                        :velocity, NOW(), NOW()
                    )
                    ON CONFLICT (post_id, platform) DO UPDATE SET
                        total_impressions = GREATEST(excluded.total_impressions, post_analytics_summary.total_impressions),
                        total_reach = GREATEST(excluded.total_reach, post_analytics_summary.total_reach),
                        total_likes = GREATEST(excluded.total_likes, post_analytics_summary.total_likes),
                        total_comments = GREATEST(excluded.total_comments, post_analytics_summary.total_comments),
                        peak_reach_velocity = GREATEST(excluded.peak_reach_velocity, post_analytics_summary.peak_reach_velocity),
                        peak_velocity_at = CASE
                            WHEN excluded.peak_reach_velocity > post_analytics_summary.peak_reach_velocity
                            THEN NOW() ELSE post_analytics_summary.peak_velocity_at END,
                        last_updated_at = NOW()
                """),
                {
                    "tenant_id": tenant_id,
                    "post_id": post_id,
                    "platform": snapshot["platform"],
                    "impressions": snapshot["impressions"],
                    "reach": snapshot["reach"],
                    "likes": snapshot["likes"],
                    "comments": snapshot["comments"],
                    "velocity": snapshot["reach_velocity"],
                },
            )
        await session.commit()


async def _get_last_snapshot(post_id: str, platform: str) -> Optional[dict]:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT reach, seconds_since_publish, recorded_at FROM telemetry_timeseries
                WHERE post_id = :pid AND platform = :platform
                ORDER BY recorded_at DESC LIMIT 1
            """),
            {"pid": post_id, "platform": platform},
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def _load_post(post_id: str, tenant_id: str) -> Optional[dict]:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM posts WHERE id=:pid AND tenant_id=:tid"),
            {"pid": post_id, "tid": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def _stop_high_freq_polling(post_id: str, tenant_id: str) -> None:
    """Remove post from the high-frequency Redis polling set."""
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await r.srem(f"tenant:{tenant_id}:hf_polling", post_id)


# ── Math Utilities ────────────────────────────────────────────────────────────

def _compute_velocity(current_reach: int, prev_snapshot: Optional[dict]) -> float:
    """Reach gained per second since last measurement."""
    if not prev_snapshot:
        return 0.0
    prev_reach = prev_snapshot.get("reach", 0) or 0
    prev_seconds = prev_snapshot.get("seconds_since_publish", 0) or 0
    current_seconds = (
        datetime.now(timezone.utc)
        - datetime.fromisoformat(prev_snapshot.get("recorded_at", datetime.now(timezone.utc).isoformat()))
    ).total_seconds()
    if current_seconds <= 0:
        return 0.0
    return round((current_reach - prev_reach) / current_seconds, 4)


def _compute_engagement_rate(data: dict, reach: int) -> float:
    if reach <= 0:
        return 0.0
    total_eng = (
        data.get("likes", 0) + data.get("like_count", 0) +
        data.get("comments", 0) + data.get("comment_count", 0) +
        data.get("shares", 0) + data.get("saves", 0)
    )
    return round(total_eng / reach, 6)
