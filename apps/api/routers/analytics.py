"""Analytics router — serve time-series telemetry, reach velocity, and rollup data."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter()


@router.get("/posts/{post_id}/velocity")
async def get_reach_velocity(
    post_id: str,
    platform: str = Query(default=None),
    limit: int = Query(default=300, le=3600),   # Last N seconds of data
    db: AsyncSession = Depends(get_db),
):
    """
    Return per-second reach velocity time-series for a post.
    Used by the ReachVelocityChart Recharts component.
    """
    query = """
        SELECT seconds_since_publish, reach_velocity, reach, impressions,
               engagement_rate, recorded_at, platform
        FROM telemetry_timeseries
        WHERE post_id = :pid
    """
    params: dict = {"pid": post_id}
    if platform:
        query += " AND platform = :platform"
        params["platform"] = platform
    query += " ORDER BY recorded_at DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = [dict(r) for r in result.mappings().all()]
    # Return in ascending time order for charting
    return {"post_id": post_id, "data": list(reversed(rows))}


@router.get("/posts/{post_id}/retention")
async def get_video_retention(
    post_id: str,
    platform: str = Query(default="instagram"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return video/Reel retention curve data.
    Used by the VideoRetentionCurve Recharts component.
    """
    result = await db.execute(text("""
        SELECT video_retention_curve, avg_watch_duration_s, recorded_at
        FROM telemetry_timeseries
        WHERE post_id = :pid AND platform = :platform
          AND video_retention_curve IS NOT NULL
        ORDER BY recorded_at DESC
        LIMIT 1
    """), {"pid": post_id, "platform": platform})
    row = result.mappings().first()
    if not row:
        return {"post_id": post_id, "retention_curve": {}}
    return {"post_id": post_id, "retention_curve": row["video_retention_curve"],
            "avg_watch_duration_s": row["avg_watch_duration_s"]}


@router.get("/posts/{post_id}/summary")
async def get_post_analytics_summary(
    post_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Full analytics summary for a post — all platforms."""
    result = await db.execute(text("""
        SELECT * FROM post_analytics_summary
        WHERE post_id = :pid
        ORDER BY platform
    """), {"pid": post_id})
    rows = [dict(r) for r in result.mappings().all()]
    return {"post_id": post_id, "platforms": rows}


@router.get("/dashboard/cross-platform")
async def get_cross_platform_analytics(
    days: int = Query(default=30, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-platform analytics for the dashboard Recharts charts.
    Returns daily rollup data for all platforms over the specified period.
    """
    result = await db.execute(text("""
        SELECT date, platform,
               total_posts, total_impressions, total_reach,
               total_engagement, avg_engagement_rate, total_leads
        FROM daily_analytics_rollup
        WHERE date >= CURRENT_DATE - INTERVAL ':days days'
        ORDER BY date ASC, platform
    """.replace(":days", str(days))))
    rows = [dict(r) for r in result.mappings().all()]
    return {"days": days, "data": rows}


@router.get("/dashboard/conversion-funnel")
async def get_conversion_funnel(
    post_id: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Lead magnet conversion funnel data.
    Returns: Impressions → Trigger Comments → DMs Sent → DMs Delivered → Converted Leads
    """
    where = "WHERE cl.tenant_id = current_tenant_id()"
    params: dict = {}
    if post_id:
        where += " AND cl.post_id = :pid"
        params["pid"] = post_id

    result = await db.execute(text(f"""
        SELECT
            SUM(pas.total_impressions) as total_impressions,
            SUM(pas.total_trigger_comments) as total_trigger_comments,
            SUM(pas.total_dms_sent) as total_dms_sent,
            COUNT(cl.id) FILTER (WHERE cl.dm_status = 'sent') as dms_delivered,
            COUNT(cl.id) FILTER (WHERE cl.is_converted = TRUE) as converted_leads,
            ROUND(
                COUNT(cl.id) FILTER (WHERE cl.dm_status = 'sent')::numeric
                / NULLIF(SUM(pas.total_trigger_comments), 0) * 100, 1
            ) as dm_conversion_pct
        FROM captured_leads cl
        JOIN post_analytics_summary pas ON pas.post_id = cl.post_id
        {where}
    """), params)
    row = result.mappings().first()
    return dict(row) if row else {}


@router.get("/dashboard/top-posts")
async def get_top_performing_posts(
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top posts by performance score for analytics command center."""
    result = await db.execute(text("""
        SELECT
            p.id, p.title, p.published_at,
            SUM(pas.total_reach) as total_reach,
            SUM(pas.total_leads_captured) as total_leads,
            AVG(pas.performance_score) as avg_score,
            MAX(pas.peak_reach_velocity) as peak_velocity
        FROM posts p
        JOIN post_analytics_summary pas ON pas.post_id = p.id
        WHERE p.status = 'PUBLISHED'
        GROUP BY p.id
        ORDER BY avg_score DESC NULLS LAST
        LIMIT :limit
    """), {"limit": limit})
    rows = [dict(r) for r in result.mappings().all()]
    return {"top_posts": rows}
