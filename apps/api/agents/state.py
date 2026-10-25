"""
Shared LangGraph AgentState TypedDict.
All agents read from and write to this single state object,
which is persisted in Redis via LangGraph's checkpointer.
"""
from __future__ import annotations
from typing import TypedDict, Annotated, Optional, Literal
from operator import add
import operator


# ── Sub-structures ────────────────────────────────────────────────────────────

class TrendingTopic(TypedDict):
    topic: str
    volume: str            # "high" | "medium" | "low"
    platforms: list[str]
    hashtags: list[str]
    viral_hook: str


class NewsjackAlert(TypedDict):
    headline: str
    source_url: str
    summary: str
    company_name: str
    event_type: str        # "layoff" | "mass_hiring" | "ipo" | "acquisition"
    severity: str          # "URGENT" | "high" | "medium" | "low"
    relevance_score: float
    detected_at: str       # ISO8601


class CarouselSlide(TypedDict):
    slide_number: int
    headline: str
    body_text: str
    visual_description: str   # Instruction for renderer
    cta: Optional[str]        # Only last slide


class PlatformContent(TypedDict, total=False):
    # LinkedIn
    linkedin_text_post: str
    linkedin_carousel_slides: list[CarouselSlide]
    linkedin_carousel_pdf_url: str
    linkedin_cta_keyword: str
    # Instagram
    instagram_caption: str
    instagram_carousel_slides: list[CarouselSlide]
    instagram_carousel_png_urls: list[str]
    instagram_reel_script: str
    instagram_cta_keyword: str
    # Twitter/X
    twitter_thread: list[str]
    twitter_cta_keyword: str
    # Facebook
    facebook_post: str
    facebook_cta_keyword: str


class HITLRevision(TypedDict):
    revision_number: int
    human_feedback: str
    snapshot_before: dict
    timestamp: str


class LeadEntry(TypedDict):
    platform: str
    platform_user_id: str
    platform_username: str
    comment_text: str
    comment_id: str
    trigger_keyword: str
    dm_status: str


class TelemetrySnapshot(TypedDict):
    post_id: str
    platform: str
    recorded_at: str
    seconds_since_publish: int
    impressions: int
    reach: int
    reach_velocity: float
    likes: int
    comments: int
    engagement_rate: float


# ── Master AgentState ────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Identity
    tenant_id: str
    run_id: str            # Unique per pipeline execution

    # ── Agent 1 outputs ──────────────────────────────────────────────────────
    trending_topics: list[TrendingTopic]
    newsjack_alerts: list[NewsjackAlert]
    active_newsjack: Optional[NewsjackAlert]   # The one being actioned
    seo_keywords: list[dict]
    research_sources: list[str]
    is_urgent_newsjack: bool

    # ── Agent 2 outputs ──────────────────────────────────────────────────────
    post_title: str
    platform_content: PlatformContent
    suggested_cta_keyword: str
    lead_magnet_id: Optional[str]
    platforms_to_publish: list[str]

    # ── Agent 3 (HITL) state ─────────────────────────────────────────────────
    post_status: Literal[
        "DRAFTING",
        "AWAITING_HUMAN_APPROVAL",
        "URGENT_NEWSJACK_APPROVAL",
        "REVISION_REQUESTED",
        "APPROVED",
        "SCHEDULED",
        "PUBLISHED",
        "FAILED",
    ]
    hitl_revisions: Annotated[list[HITLRevision], add]   # Append-only
    human_feedback: Optional[str]
    post_id: Optional[str]   # Set after DB insert

    # ── Agent 4 outputs ──────────────────────────────────────────────────────
    captured_leads: Annotated[list[LeadEntry], add]

    # ── Agent 5 outputs ──────────────────────────────────────────────────────
    telemetry_snapshots: Annotated[list[TelemetrySnapshot], add]
    performance_score: Optional[float]

    # ── Pipeline metadata ────────────────────────────────────────────────────
    errors: Annotated[list[str], add]
    current_agent: str
    tokens_used: Annotated[int, operator.add]
