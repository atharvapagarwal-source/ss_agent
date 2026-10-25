"""
HITL Approval Router — human actions on the approval queue.
These endpoints are called by the coach portal when they:
  - Approve and publish a post
  - Approve and schedule a post
  - Request a revision with natural language feedback
  - Manually edit content inline
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db, set_tenant_context
from agents.agent3_hitl import handle_approval, handle_revision_request
from agents.orchestrator import get_graph, resume_after_approval

router = APIRouter()


# ── Request/Response schemas ──────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    run_id: str
    schedule_at: Optional[str] = None   # ISO8601 datetime; None = publish now


class RevisionRequest(BaseModel):
    run_id: str
    feedback: str   # Natural language revision instruction


class InlineEditRequest(BaseModel):
    platform_content: dict   # Updated platform_content JSON


class HITLStatusResponse(BaseModel):
    post_id: str
    status: str
    revision_count: int
    post_title: str
    platform_content: dict
    is_urgent: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/queue")
async def get_approval_queue(
    db: AsyncSession = Depends(get_db),
    # TODO: inject current_user from JWT middleware
):
    """
    Return all posts awaiting human approval for this tenant,
    sorted with URGENT_NEWSJACK_APPROVAL first.
    """
    # RLS ensures tenant isolation — session var set by auth middleware
    result = await db.execute(text("""
        SELECT
            p.id, p.title, p.status, p.is_urgent_newsjack,
            p.revision_count, p.platform_content, p.created_at,
            p.scheduled_publish_at, p.dm_trigger_keywords,
            na.headline as newsjack_headline, na.company_name
        FROM posts p
        LEFT JOIN newsjack_alerts na ON na.id = p.newsjack_alert_id
        WHERE p.status IN ('AWAITING_HUMAN_APPROVAL', 'URGENT_NEWSJACK_APPROVAL', 'REVISION_REQUESTED')
        ORDER BY p.is_urgent_newsjack DESC, p.created_at ASC
    """))
    posts = [dict(row) for row in result.mappings().all()]
    return {"queue": posts, "total": len(posts)}


@router.get("/{post_id}")
async def get_post_detail(
    post_id: str,
    db: AsyncSession = Depends(get_db),
) -> HITLStatusResponse:
    """Full post detail with content preview for the HITL Approval Studio."""
    result = await db.execute(text("""
        SELECT p.*, 
               array_agg(
                   json_build_object(
                       'revision_number', hr.revision_number,
                       'human_feedback', hr.human_feedback,
                       'from_status', hr.from_status,
                       'actioned_at', hr.actioned_at
                   ) ORDER BY hr.revision_number
               ) FILTER (WHERE hr.id IS NOT NULL) as revisions
        FROM posts p
        LEFT JOIN hitl_revisions hr ON hr.post_id = p.id
        WHERE p.id = :pid
        GROUP BY p.id
    """), {"pid": post_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return dict(row)


@router.post("/{post_id}/approve")
async def approve_post(
    post_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a post for immediate publish or schedule.
    Resumes the LangGraph pipeline through the publisher_node.
    CRITICAL: This is the ONLY path to publishing — no bypasses exist.
    """
    # Update DB status
    result = await handle_approval(
        post_id=post_id,
        tenant_id="INJECT_FROM_JWT",  # TODO: inject from JWT
        user_id="INJECT_FROM_JWT",
        schedule_at=body.schedule_at,
        run_id=body.run_id,
    )

    # Resume LangGraph after human approval
    await resume_after_approval(run_id=body.run_id, tenant_id="INJECT_FROM_JWT")

    return result


@router.post("/{post_id}/revise")
async def request_revision(
    post_id: str,
    body: RevisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a natural language revision prompt.
    Routes back to Agent 2, which applies changes and returns to HITL.
    """
    if not body.feedback or len(body.feedback.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Feedback must be at least 5 characters",
        )

    graph = get_graph()
    result = await handle_revision_request(
        post_id=post_id,
        tenant_id="INJECT_FROM_JWT",   # TODO: inject from JWT
        user_id="INJECT_FROM_JWT",
        feedback=body.feedback,
        run_id=body.run_id,
        graph=graph,
    )
    return result


@router.patch("/{post_id}/inline-edit")
async def inline_edit_post(
    post_id: str,
    body: InlineEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Save manual inline edits to platform_content without triggering AI re-generation.
    Coach can directly edit text/slides in the HITL Studio UI.
    """
    await db.execute(text("""
        UPDATE posts SET
            platform_content = :content::jsonb,
            updated_at = NOW()
        WHERE id = :pid
    """), {"content": __import__("json").dumps(body.platform_content), "pid": post_id})
    await db.commit()
    return {"status": "updated", "post_id": post_id}


@router.post("/{post_id}/reject")
async def reject_post(post_id: str, db: AsyncSession = Depends(get_db)):
    """Archive a post that the coach decides not to publish."""
    await db.execute(text("""
        UPDATE posts SET status = 'ARCHIVED', updated_at = NOW()
        WHERE id = :pid
    """), {"pid": post_id})
    await db.commit()
    return {"status": "archived", "post_id": post_id}
