"""Posts router — list, create, trigger pipeline, and manage post lifecycle."""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from database import get_db

router = APIRouter()


class TriggerPipelineRequest(BaseModel):
    trigger: str = "manual"    # "manual" | "newsjack" | "scheduled"
    newsjack_alert_id: Optional[str] = None


@router.get("/")
async def list_posts(
    status: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List tenant's posts with optional status and platform filters."""
    conditions = ["1=1"]
    params: dict = {"offset": (page - 1) * page_size, "limit": page_size}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if platform:
        conditions.append(":platform = ANY(platforms_to_publish)")
        params["platform"] = platform

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT id, title, status, is_urgent_newsjack, platforms_to_publish,
               scheduled_publish_at, published_at, revision_count, created_at
        FROM posts WHERE {where}
        ORDER BY created_at DESC LIMIT :limit OFFSET :offset
    """), params)
    count = await db.execute(text(f"SELECT COUNT(*) FROM posts WHERE {where}"),
                              {k: v for k, v in params.items() if k not in ("offset", "limit")})
    return {"posts": [dict(r) for r in result.mappings().all()], "total": count.scalar()}


@router.post("/trigger-pipeline")
async def trigger_agent_pipeline(
    body: TriggerPipelineRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the full Agent 1→2→3 pipeline for the tenant."""
    from agents.orchestrator import run_full_pipeline
    # TODO: extract tenant_id from JWT
    tenant_id = "INJECT_FROM_JWT"
    result = await run_full_pipeline(tenant_id=tenant_id, trigger=body.trigger)
    return result


@router.get("/{post_id}")
async def get_post(post_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM posts WHERE id=:id"), {"id": post_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Post not found")
    return dict(row)


@router.delete("/{post_id}")
async def archive_post(post_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(text("UPDATE posts SET status='ARCHIVED' WHERE id=:id"), {"id": post_id})
    await db.commit()
    return {"archived": True}
