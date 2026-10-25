"""SuperAdmin Tenants router — tenant lifecycle and feature flag management."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from typing import Optional

router = APIRouter()


class TenantUpdateRequest(BaseModel):
    status: Optional[str] = None
    tier: Optional[str] = None
    feature_newsjack: Optional[bool] = None
    feature_comment_to_dm: Optional[bool] = None
    feature_analytics_l2: Optional[bool] = None
    monthly_post_quota: Optional[int] = None
    monthly_dm_quota: Optional[int] = None


@router.get("/")
async def list_tenants(db: AsyncSession = Depends(get_db)):
    """SuperAdmin: List all tenants with quota summary."""
    result = await db.execute(text("SELECT * FROM tenant_quota_summary ORDER BY business_name"))
    return {"tenants": [dict(r) for r in result.mappings().all()]}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM tenants WHERE id=:id"), {"id": tenant_id}
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Tenant not found")
    return dict(row)


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """SuperAdmin: Update tenant status, tier, feature flags, or quotas."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = tenant_id
    await db.execute(
        text(f"UPDATE tenants SET {set_clause}, updated_at=NOW() WHERE id=:id"), updates
    )
    await db.commit()
    return {"tenant_id": tenant_id, "updated": list(body.model_dump(exclude_none=True).keys())}


@router.delete("/{tenant_id}")
async def suspend_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(
        text("UPDATE tenants SET status='suspended' WHERE id=:id"), {"id": tenant_id}
    )
    await db.commit()
    return {"tenant_id": tenant_id, "status": "suspended"}


@router.get("/health/system")
async def system_health(db: AsyncSession = Depends(get_db)):
    """SuperAdmin: System health snapshot — webhook queue depth, API limits, error rates."""
    webhook_pending = await db.execute(text("SELECT COUNT(*) FROM webhook_event_log WHERE processed=FALSE"))
    throttled_apis = await db.execute(text("SELECT COUNT(*) FROM api_rate_limit_tracker WHERE is_throttled=TRUE"))
    dm_failed = await db.execute(text("SELECT COUNT(*) FROM dm_automations WHERE status='failed'"))
    return {
        "webhook_queue_depth": webhook_pending.scalar(),
        "throttled_api_endpoints": throttled_apis.scalar(),
        "failed_dm_automations": dm_failed.scalar(),
    }
