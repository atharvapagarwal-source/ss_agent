"""
Agent 2: Multi-Format Content & Carousel Creator.

Responsibilities:
  - Reads Agent 1 research/newsjack data from AgentState.
  - Uses tenant brand profile (niche, tone, colors, audience).
  - Generates platform-specific content for LinkedIn, Instagram, X, Facebook.
  - Triggers carousel renderer microservice for PDF/PNG generation.
  - Integrates lead-magnet CTAs and suggests trigger keywords.
"""
from __future__ import annotations
import json
import httpx
import structlog
from datetime import datetime, timezone
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from agents.state import AgentState, CarouselSlide, PlatformContent

logger = structlog.get_logger(__name__)

llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_PRO_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.75,
)

# ── Master Content Generation Prompt ─────────────────────────────────────────

CONTENT_SYSTEM = """You are an elite social media content strategist and ghostwriter for career coaches.
You write in the coach's exact brand voice and create highly-engaging, platform-native content.

Your output MUST be valid JSON matching this schema exactly:
{{
  "post_title": "string (internal title for approval queue)",
  "suggested_cta_keyword": "string (e.g. RESUME, GUIDE, CHECKLIST, TOOLKIT)",
  
  "linkedin": {{
    "text_post": "string (1800-2200 chars, hook + value + CTA, uses line breaks for readability)",
    "carousel_slides": [
      {{
        "slide_number": 1,
        "headline": "string (max 8 words, bold statement)",
        "body_text": "string (max 40 words, punchy bullet points or short sentences)",
        "visual_description": "string (describe background style, icon, image concept for renderer)",
        "cta": null
      }}
    ],
    "cta_keyword": "string"
  }},
  
  "instagram": {{
    "caption": "string (max 2200 chars, hooks in first line, 20-30 hashtags at end)",
    "carousel_slides": [...],
    "reel_script": "string (60-90 second script with hook/value/CTA structure, includes on-screen text cues)",
    "cta_keyword": "string"
  }},
  
  "twitter": {{
    "thread": ["tweet1 (hook, max 280 chars)", "tweet2 (value)", "...", "last tweet (CTA)"],
    "cta_keyword": "string"
  }},
  
  "facebook": {{
    "post_text": "string (community-focused, conversational, 300-600 chars, ends with engagement question)",
    "cta_keyword": "string"
  }}
}}

Rules:
- LinkedIn carousel: exactly 6-10 slides. Slide 1 = bold cover hook. Last slide = CTA.
- Instagram carousel: exactly 6-8 slides, optimized for 1080x1350px vertical format.  
- Twitter thread: 5-8 tweets. Tweet 1 must start with a number or strong statement.
- Every platform must end with: "Comment '[KEYWORD]' below and I'll DM you [lead magnet description]"
- Use the brand voice/tone provided. Avoid generic corporate language.
- For URGENT newsjacks: lead with the breaking news and pivot to coaching advice within 2 sentences.
"""


# ── Core Node Function ────────────────────────────────────────────────────────

async def agent2_creator(state: AgentState) -> dict:
    """
    LangGraph node: Multi-format content generator.
    Takes Agent 1 research and generates all platform content.
    """
    tenant_id = state["tenant_id"]
    log = logger.bind(agent="agent2", tenant_id=tenant_id)
    log.info("Agent 2 started: content creation")

    try:
        # ── Step 1: Load brand profile & lead magnet ──────────────────────────
        brand = await _load_full_brand_context(tenant_id)
        lead_magnet = await _get_default_lead_magnet(tenant_id)

        # ── Step 2: Build rich context for the LLM ───────────────────────────
        context = _build_content_context(state, brand, lead_magnet)

        # ── Step 3: Handle revision feedback (if re-routed from Agent 3) ─────
        revision_prompt = state.get("human_feedback")
        if revision_prompt:
            log.info("Processing revision request", feedback=revision_prompt[:100])
            return await _handle_revision(state, context, revision_prompt, brand, lead_magnet, log)

        # ── Step 4: Generate all platform content ────────────────────────────
        response = await llm.ainvoke([
            SystemMessage(content=CONTENT_SYSTEM),
            HumanMessage(content=context),
        ])

        content_data = _parse_json_response(response.content)
        tokens_used = getattr(response, "usage_metadata", {}).get("total_token_count", 0)

        # ── Step 5: Build platform_content dict ──────────────────────────────
        platform_content = _extract_platform_content(content_data)

        # ── Step 6: Trigger carousel renderer for LinkedIn & Instagram ────────
        linkedin_slides = content_data.get("linkedin", {}).get("carousel_slides", [])
        instagram_slides = content_data.get("instagram", {}).get("carousel_slides", [])

        carousel_urls = await _render_carousels(
            tenant_id=tenant_id,
            post_id=state.get("run_id", "preview"),
            brand=brand,
            linkedin_slides=linkedin_slides,
            instagram_slides=instagram_slides,
        )

        if carousel_urls.get("linkedin_pdf"):
            platform_content["linkedin_carousel_pdf_url"] = carousel_urls["linkedin_pdf"]
        if carousel_urls.get("instagram_pngs"):
            platform_content["instagram_carousel_png_urls"] = carousel_urls["instagram_pngs"]

        is_urgent = state.get("is_urgent_newsjack", False)

        log.info(
            "Agent 2 complete",
            platforms=list(platform_content.keys()),
            urgent=is_urgent,
            tokens=tokens_used,
        )

        return {
            "post_title": content_data.get("post_title", "Untitled Post"),
            "platform_content": platform_content,
            "suggested_cta_keyword": content_data.get("suggested_cta_keyword", "GUIDE"),
            "lead_magnet_id": lead_magnet.get("id") if lead_magnet else None,
            "platforms_to_publish": ["linkedin", "instagram", "twitter", "facebook"],
            "post_status": (
                "URGENT_NEWSJACK_APPROVAL" if is_urgent else "AWAITING_HUMAN_APPROVAL"
            ),
            "human_feedback": None,   # Clear feedback after processing
            "current_agent": "agent3_hitl",
            "tokens_used": tokens_used,
        }

    except Exception as exc:
        log.error("Agent 2 failed", error=str(exc))
        return {
            "errors": [f"agent2_creator: {exc}"],
            "post_status": "AWAITING_HUMAN_APPROVAL",
            "current_agent": "agent3_hitl",
        }


# ── Revision Handler ──────────────────────────────────────────────────────────

async def _handle_revision(
    state: AgentState,
    base_context: str,
    revision_prompt: str,
    brand: dict,
    lead_magnet: Optional[dict],
    log,
) -> dict:
    """Apply natural-language revision instructions to existing content."""
    existing = json.dumps(state.get("platform_content", {}), indent=2)
    revision_count = len(state.get("hitl_revisions", []))

    response = await llm.ainvoke([
        SystemMessage(content=CONTENT_SYSTEM),
        HumanMessage(content=(
            f"REVISION REQUEST #{revision_count + 1}:\n{revision_prompt}\n\n"
            f"EXISTING CONTENT TO MODIFY:\n{existing[:6000]}\n\n"
            f"BRAND CONTEXT:\n{base_context}\n\n"
            "Apply ONLY the requested changes. Keep everything else intact. "
            "Return the full updated JSON."
        )),
    ])

    content_data = _parse_json_response(response.content)
    tokens_used = getattr(response, "usage_metadata", {}).get("total_token_count", 0)

    # Re-render carousels if slide content changed
    linkedin_slides = content_data.get("linkedin", {}).get("carousel_slides", [])
    instagram_slides = content_data.get("instagram", {}).get("carousel_slides", [])
    carousel_urls = await _render_carousels(
        tenant_id=state["tenant_id"],
        post_id=state.get("post_id") or state.get("run_id", "preview"),
        brand=brand,
        linkedin_slides=linkedin_slides,
        instagram_slides=instagram_slides,
    )

    platform_content = _extract_platform_content(content_data)
    if carousel_urls.get("linkedin_pdf"):
        platform_content["linkedin_carousel_pdf_url"] = carousel_urls["linkedin_pdf"]
    if carousel_urls.get("instagram_pngs"):
        platform_content["instagram_carousel_png_urls"] = carousel_urls["instagram_pngs"]

    return {
        "platform_content": platform_content,
        "post_title": content_data.get("post_title", state.get("post_title", "Untitled")),
        "post_status": "AWAITING_HUMAN_APPROVAL",
        "human_feedback": None,
        "current_agent": "agent3_hitl",
        "tokens_used": tokens_used,
    }


# ── Carousel Renderer Client ──────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
async def _render_carousels(
    tenant_id: str,
    post_id: str,
    brand: dict,
    linkedin_slides: list[CarouselSlide],
    instagram_slides: list[CarouselSlide],
) -> dict:
    """
    Calls the Playwright carousel renderer microservice to generate
    LinkedIn PDF and Instagram PNG slide decks.
    Returns dict with 'linkedin_pdf' URL and 'instagram_pngs' list.
    """
    if not linkedin_slides and not instagram_slides:
        return {}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "tenant_id": tenant_id,
                "post_id": post_id,
                "brand": brand,
                "linkedin_slides": linkedin_slides,
                "instagram_slides": instagram_slides,
            }
            response = await client.post(
                f"{settings.CAROUSEL_RENDERER_URL}/render",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.warning("Carousel renderer unavailable, skipping", error=str(e))
        return {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_content_context(state: AgentState, brand: dict, lead_magnet: Optional[dict]) -> str:
    """Build the rich context string fed to the LLM."""
    topics = state.get("trending_topics", [])[:5]
    newsjack = state.get("active_newsjack")
    keywords = state.get("seo_keywords", [])[:10]
    is_urgent = state.get("is_urgent_newsjack", False)

    lines = [
        f"COACHING NICHE: {brand.get('coaching_niche', 'career coaching')}",
        f"TARGET AUDIENCE: {brand.get('target_audience', 'professionals')}",
        f"BRAND TONE: {brand.get('tone_of_voice', 'empathetic, authoritative')}",
        "",
    ]

    if is_urgent and newsjack:
        lines += [
            "⚡ URGENT NEWSJACK MODE — Prioritize this breaking news above everything:",
            f"  Headline: {newsjack['headline']}",
            f"  Summary: {newsjack['summary']}",
            f"  Company: {newsjack.get('company_name', 'N/A')}",
            f"  Event: {newsjack['event_type']}",
            "",
        ]

    if topics:
        lines.append("TRENDING TOPICS TO USE:")
        for t in topics:
            lines.append(f"  - {t['topic']} (hook: {t.get('viral_hook', '')})")
        lines.append("")

    if keywords:
        lines.append("SEO KEYWORDS TO WEAVE IN:")
        lines.append(", ".join(k["keyword"] for k in keywords))
        lines.append("")

    if lead_magnet:
        lines += [
            f"LEAD MAGNET: '{lead_magnet['name']}' — {lead_magnet.get('description', '')}",
            f"DEFAULT TRIGGER KEYWORD: {lead_magnet.get('default_keyword', 'GUIDE')}",
            f"DELIVERY URL (for context only, don't include in post): {lead_magnet.get('delivery_url', '')}",
            "",
        ]

    if brand.get("system_prompt_override"):
        lines += ["ADDITIONAL BRAND INSTRUCTIONS:", brand["system_prompt_override"], ""]

    return "\n".join(lines)


def _extract_platform_content(data: dict) -> PlatformContent:
    """Map raw LLM JSON into typed PlatformContent dict."""
    content: PlatformContent = {}
    li = data.get("linkedin", {})
    ig = data.get("instagram", {})
    tw = data.get("twitter", {})
    fb = data.get("facebook", {})

    if li:
        content["linkedin_text_post"] = li.get("text_post", "")
        content["linkedin_carousel_slides"] = li.get("carousel_slides", [])
        content["linkedin_cta_keyword"] = li.get("cta_keyword", "GUIDE")
    if ig:
        content["instagram_caption"] = ig.get("caption", "")
        content["instagram_carousel_slides"] = ig.get("carousel_slides", [])
        content["instagram_reel_script"] = ig.get("reel_script", "")
        content["instagram_cta_keyword"] = ig.get("cta_keyword", "GUIDE")
    if tw:
        content["twitter_thread"] = tw.get("thread", [])
        content["twitter_cta_keyword"] = tw.get("cta_keyword", "GUIDE")
    if fb:
        content["facebook_post"] = fb.get("post_text", "")
        content["facebook_cta_keyword"] = fb.get("cta_keyword", "GUIDE")

    return content


def _parse_json_response(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {}


async def _load_full_brand_context(tenant_id: str) -> dict:
    from database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT tbp.*, t.brand_colors, t.brand_fonts, t.logo_url
                FROM tenant_brand_profiles tbp
                JOIN tenants t ON t.id = tbp.tenant_id
                WHERE tbp.tenant_id = :tid
            """),
            {"tid": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else {}


async def _get_default_lead_magnet(tenant_id: str) -> Optional[dict]:
    from database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, name, description, magnet_type, delivery_url, 
                       default_keyword, dm_message_template
                FROM lead_magnets
                WHERE tenant_id = :tid AND is_active = TRUE
                ORDER BY total_leads_captured DESC
                LIMIT 1
            """),
            {"tid": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None
