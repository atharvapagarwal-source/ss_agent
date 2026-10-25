"""Newsjack feed router — trending alerts and urgent newsjack management."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter()


@router.get("/feed")
async def get_newsjack_feed(
    severity: str = Query(default=None),
    unactioned_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Return newsjack alerts for the coach's live feed, URGENT first."""
    query = "SELECT * FROM newsjack_alerts WHERE 1=1"
    params: dict = {}
    if severity:
        query += " AND severity = :severity"
        params["severity"] = severity
    if unactioned_only:
        query += " AND is_actioned = FALSE"
    query += " ORDER BY severity DESC, detected_at DESC LIMIT 50"

    result = await db.execute(text(query), params)
    return {"alerts": [dict(r) for r in result.mappings().all()]}


@router.post("/{alert_id}/generate-post")
async def generate_post_from_newsjack(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """1-click 'Generate Response Post' from a newsjack alert."""
    from agents.orchestrator import run_full_pipeline

    # Load alert
    result = await db.execute(text("SELECT * FROM newsjack_alerts WHERE id=:id"), {"id": alert_id})
    alert = result.mappings().first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(404, "Alert not found")

    # Run pipeline with urgency flag
    tenant_id = str(alert["tenant_id"])
    pipeline_result = await run_full_pipeline(tenant_id=tenant_id, trigger="newsjack_manual")

    # Mark alert as actioned
    await db.execute(text(
        "UPDATE newsjack_alerts SET is_actioned=TRUE, actioned_post_id=NULL WHERE id=:id"
    ), {"id": alert_id})
    await db.commit()

    return {"run_id": pipeline_result["run_id"], "status": "pipeline_started"}


@router.get("/trends")
async def get_trend_reports(
    limit: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Return latest trend research reports for the coach dashboard."""
    result = await db.execute(text("""
        SELECT id, generated_at, niche_context, trending_topics, seo_keywords
        FROM trend_reports
        ORDER BY generated_at DESC
        LIMIT :limit
    """), {"limit": limit})
    return {"reports": [dict(r) for r in result.mappings().all()]}
