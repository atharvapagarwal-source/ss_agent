"""Lead CRM router — captured leads table with filters and CSV export."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
import csv
import io

router = APIRouter()


@router.get("/")
async def list_leads(
    platform: str = Query(default=None),
    dm_status: str = Query(default=None),
    post_id: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated leads with filters. RLS enforces tenant isolation."""
    conditions = ["1=1"]
    params: dict = {"offset": (page - 1) * page_size, "limit": page_size}

    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    if dm_status:
        conditions.append("dm_status = :dm_status")
        params["dm_status"] = dm_status
    if post_id:
        conditions.append("post_id = :post_id")
        params["post_id"] = post_id

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT
            cl.id, cl.platform, cl.platform_username, cl.platform_display_name,
            cl.trigger_keyword, cl.original_comment_text,
            cl.dm_status, cl.dm_sent_at, cl.is_converted,
            cl.created_at, p.title as post_title, lm.name as lead_magnet_name
        FROM captured_leads cl
        LEFT JOIN posts p ON p.id = cl.post_id
        LEFT JOIN lead_magnets lm ON lm.id = cl.lead_magnet_id
        WHERE {where}
        ORDER BY cl.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params)

    # Count total
    count_result = await db.execute(text(f"""
        SELECT COUNT(*) FROM captured_leads cl WHERE {where}
    """), {k: v for k, v in params.items() if k not in ("offset", "limit")})

    total = count_result.scalar()
    leads = [dict(r) for r in result.mappings().all()]
    return {"leads": leads, "total": total, "page": page, "page_size": page_size}


@router.get("/export.csv")
async def export_leads_csv(db: AsyncSession = Depends(get_db)):
    """Export all leads as CSV for the coach."""
    result = await db.execute(text("""
        SELECT
            cl.platform, cl.platform_username, cl.platform_display_name,
            cl.trigger_keyword, cl.original_comment_text,
            cl.dm_status, cl.dm_sent_at, cl.is_converted, cl.created_at,
            p.title as post_title
        FROM captured_leads cl
        LEFT JOIN posts p ON p.id = cl.post_id
        ORDER BY cl.created_at DESC
    """))
    rows = [dict(r) for r in result.mappings().all()]

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/stats")
async def get_lead_stats(db: AsyncSession = Depends(get_db)):
    """Summary stats for the Lead CRM dashboard card."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_leads,
            COUNT(*) FILTER (WHERE dm_status = 'sent') as dms_sent,
            COUNT(*) FILTER (WHERE dm_status = 'failed') as dms_failed,
            COUNT(*) FILTER (WHERE is_converted = TRUE) as converted,
            COUNT(DISTINCT platform) as platforms_active,
            COUNT(DISTINCT post_id) as posts_with_leads
        FROM captured_leads
    """))
    return dict(result.mappings().first() or {})


@router.patch("/{lead_id}/convert")
async def mark_lead_converted(lead_id: str, db: AsyncSession = Depends(get_db)):
    """Manually mark a lead as converted (e.g., booked a call)."""
    await db.execute(text("""
        UPDATE captured_leads SET is_converted=TRUE, converted_at=NOW()
        WHERE id = :id
    """), {"id": lead_id})
    await db.commit()
    return {"lead_id": lead_id, "is_converted": True}
