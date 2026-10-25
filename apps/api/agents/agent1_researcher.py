"""
Agent 1: Autonomous Trend, Keyword & Live Newsjacking Researcher.

Responsibilities:
  - Daily scheduled web/LinkedIn trend discovery for the tenant's coaching niche.
  - Every-15-minute breaking news monitor for layoffs, mass hiring, IPOs.
  - Outputs structured JSON into AgentState for Agent 2 to consume.
  - Flags URGENT_NEWSJACK events, which bypass the normal schedule.
"""
from __future__ import annotations
import json
import structlog
from datetime import datetime, timezone
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from agents.state import AgentState, TrendingTopic, NewsjackAlert

logger = structlog.get_logger(__name__)

# ── LLM & Tool Clients (Lazy-Loaded) ──────────────────────────────────────────
def get_llm() -> ChatGoogleGenerativeAI | None:
    if not settings.GEMINI_API_KEY:
        return None
    try:
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
        )
    except Exception as e:
        logger.warning("Failed to initialize ChatGoogleGenerativeAI", error=str(e))
        return None


def get_tavily() -> TavilyClient | None:
    if not settings.TAVILY_API_KEY:
        return None
    try:
        return TavilyClient(api_key=settings.TAVILY_API_KEY)
    except Exception as e:
        logger.warning("Failed to initialize TavilyClient", error=str(e))
        return None


# ── Prompts ───────────────────────────────────────────────────────────────────

TREND_RESEARCH_SYSTEM = """You are a world-class social media strategist and career coaching content researcher.
Your job is to identify the highest-engagement trending topics, viral hooks, and SEO keywords
for a career coach operating in the following niche.

Return ONLY valid JSON matching this exact schema:
{{
  "trending_topics": [
    {{
      "topic": "string",
      "volume": "high|medium|low",
      "platforms": ["instagram", "linkedin", "twitter", "facebook"],
      "hashtags": ["#tag1", "#tag2"],
      "viral_hook": "string — an attention-grabbing opening line for a post about this topic"
    }}
  ],
  "seo_keywords": [
    {{"keyword": "string", "search_volume": "high|medium|low", "difficulty": "easy|medium|hard"}}
  ],
  "sources_used": ["url1", "url2"]
}}

Be specific, actionable, and platform-aware. Prioritize topics with high emotional resonance
(career anxiety, job market fear, success stories, insider tips).
"""

NEWSJACK_SYSTEM = """You are a real-time business news analyst specializing in career impact events.
Analyze the following raw news data and identify events that are highly relevant
to a career coach's audience (job seekers, professionals, executives).

Focus on:
- Mass layoffs (any company, any size)
- Major hiring drives or job opening surges
- High-profile IPOs or acquisitions affecting employment
- Sector-wide automation or AI displacement news
- Viral "return to office" or remote work policy changes

Return ONLY valid JSON:
{{
  "alerts": [
    {{
      "headline": "string",
      "source_url": "string",
      "summary": "string (2-3 sentences max)",
      "company_name": "string",
      "event_type": "layoff|mass_hiring|ipo|acquisition|policy_change|other",
      "severity": "URGENT|high|medium|low",
      "relevance_score": 0.0,
      "coaching_angle": "string — how this coach can provide value to their audience about this news"
    }}
  ]
}}

Severity guide:
- URGENT: >1000 jobs affected OR viral news (trending on X/LinkedIn) OR FAANG/Fortune 500
- high: 200-999 jobs, well-known company
- medium: <200 jobs, smaller company
- low: minor relevance
"""


# ── Core Node Function ────────────────────────────────────────────────────────

async def agent1_researcher(state: AgentState) -> dict:
    """
    LangGraph node: Trend & Newsjack Researcher.
    Runs web searches then asks Gemini to synthesize structured insights.
    """
    tenant_id = state["tenant_id"]
    log = logger.bind(agent="agent1", tenant_id=tenant_id)
    log.info("Agent 1 started: trend research")

    try:
        # ── Step 1: Load tenant brand profile ────────────────────────────────
        brand_profile = await _load_brand_profile(tenant_id)
        niche = brand_profile.get("coaching_niche", "career coaching")
        audience = brand_profile.get("target_audience", "job seekers and professionals")
        keywords = brand_profile.get("core_keywords", [])

        # ── Step 2: Web search for trends ────────────────────────────────────
        trend_queries = [
            f"{niche} trends {datetime.now(timezone.utc).strftime('%B %Y')}",
            f"career advice {niche} LinkedIn viral",
            f"job market {niche} 2024 2025",
        ] + [f"{kw} trending" for kw in keywords[:3]]

        raw_trend_results = await _multi_search(trend_queries)

        # ── Step 3: Synthesize trends with Gemini ────────────────────────────
        llm = get_llm()
        if not llm:
            log.warning("GEMINI_API_KEY not configured, using fallback research insights")
            return {
                "trending_topics": [
                    {
                        "topic": f"Navigating Modern Executive Transitions in {niche}",
                        "volume": "high",
                        "platforms": ["linkedin", "instagram", "twitter"],
                        "hashtags": ["#career", "#leadership"],
                        "viral_hook": "Why standard career playbooks are failing senior leaders in 2026."
                    }
                ],
                "newsjack_alerts": [],
                "active_newsjack": None,
                "seo_keywords": [{"keyword": niche, "search_volume": "high", "difficulty": "medium"}],
                "research_sources": ["https://example.com"],
                "is_urgent_newsjack": False,
                "post_status": "DRAFTING",
                "current_agent": "agent2_creator",
                "tokens_used": 0,
            }

        trend_prompt = (
            f"Coaching niche: {niche}\n"
            f"Target audience: {audience}\n"
            f"Core keywords: {', '.join(keywords)}\n\n"
            f"Raw research data:\n{json.dumps(raw_trend_results, indent=2)[:8000]}"
        )
        trend_response = await llm.ainvoke([
            SystemMessage(content=TREND_RESEARCH_SYSTEM),
            HumanMessage(content=trend_prompt),
        ])
        trend_data = _parse_json_response(trend_response.content)

        # ── Step 4: Search for breaking news / newsjack events ───────────────
        news_queries = [
            "layoffs 2024 latest news site:techcrunch.com OR site:reuters.com",
            "mass hiring 2024 jobs technology",
            f"{niche} industry news hiring layoffs",
            "corporate downsizing 2024",
        ]
        raw_news = await _multi_search(news_queries, search_depth="advanced", max_results=15)

        # ── Step 5: Score newsjack relevance with Gemini ─────────────────────
        news_response = await llm.ainvoke([
            SystemMessage(content=NEWSJACK_SYSTEM),
            HumanMessage(content=(
                f"Coach niche: {niche}\nAudience: {audience}\n\n"
                f"News data:\n{json.dumps(raw_news, indent=2)[:8000]}"
            )),
        ])
        news_data = _parse_json_response(news_response.content)

        # ── Step 6: Parse & classify alerts ──────────────────────────────────
        alerts: list[NewsjackAlert] = []
        is_urgent = False
        active_newsjack = None

        for raw_alert in news_data.get("alerts", []):
            alert: NewsjackAlert = {
                "headline": raw_alert.get("headline", ""),
                "source_url": raw_alert.get("source_url", ""),
                "summary": raw_alert.get("summary", ""),
                "company_name": raw_alert.get("company_name", ""),
                "event_type": raw_alert.get("event_type", "other"),
                "severity": raw_alert.get("severity", "low"),
                "relevance_score": float(raw_alert.get("relevance_score", 0.5)),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
            alerts.append(alert)

            if alert["severity"] == "URGENT" and not is_urgent:
                is_urgent = True
                active_newsjack = alert
                log.warning("URGENT newsjack detected", headline=alert["headline"])

        # ── Step 7: Compute token usage ───────────────────────────────────────
        total_tokens = (
            getattr(trend_response, "usage_metadata", {}).get("total_token_count", 0)
            + getattr(news_response, "usage_metadata", {}).get("total_token_count", 0)
        )

        log.info(
            "Agent 1 complete",
            topics=len(trend_data.get("trending_topics", [])),
            alerts=len(alerts),
            urgent=is_urgent,
            tokens=total_tokens,
        )

        return {
            "trending_topics": trend_data.get("trending_topics", []),
            "newsjack_alerts": alerts,
            "active_newsjack": active_newsjack,
            "seo_keywords": trend_data.get("seo_keywords", []),
            "research_sources": trend_data.get("sources_used", []),
            "is_urgent_newsjack": is_urgent,
            "post_status": "URGENT_NEWSJACK_APPROVAL" if is_urgent else "DRAFTING",
            "current_agent": "agent2_creator",
            "tokens_used": total_tokens,
        }

    except Exception as exc:
        log.error("Agent 1 failed", error=str(exc))
        return {
            "errors": [f"agent1_researcher: {exc}"],
            "current_agent": "agent2_creator",
            "post_status": "DRAFTING",
            "trending_topics": [],
            "newsjack_alerts": [],
            "is_urgent_newsjack": False,
        }


# ── Standalone Newsjack Poll (called by Celery beat every 15 mins) ────────────

async def poll_newsjack_only(tenant_id: str, brand_profile: dict) -> list[NewsjackAlert]:
    """
    Lightweight newsjack-only poll — does NOT run full trend research.
    Called by the Celery beat schedule every 15 minutes per active tenant.
    """
    niche = brand_profile.get("coaching_niche", "career coaching")
    queries = [
        "breaking news layoffs today site:techcrunch.com OR site:bloomberg.com",
        "mass hiring announced today technology 2024",
        f"{niche} industry news breaking",
    ]
    raw_news = await _multi_search(queries, search_depth="basic", max_results=10)
    llm = get_llm()
    if not llm:
        return []
    response = await llm.ainvoke([
        SystemMessage(content=NEWSJACK_SYSTEM),
        HumanMessage(content=f"Niche: {niche}\n\nNews:\n{json.dumps(raw_news)[:6000]}"),
    ])
    data = _parse_json_response(response.content)
    return [
        {**a, "detected_at": datetime.now(timezone.utc).isoformat()}
        for a in data.get("alerts", [])
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _multi_search(
    queries: list[str],
    search_depth: str = "basic",
    max_results: int = 8,
) -> list[dict]:
    """Run multiple Tavily searches concurrently and merge results."""
    import asyncio
    tavily_client = get_tavily()
    if not tavily_client:
        return [
            {"title": q, "content": f"Trend developments for {q}", "url": "https://example.com"}
            for q in queries
        ]
    results = []
    tasks = [
        asyncio.to_thread(
            tavily_client.search,
            query=q,
            search_depth=search_depth,
            max_results=max_results,
            include_raw_content=False,
        )
        for q in queries
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for r in responses:
        if isinstance(r, dict):
            results.extend(r.get("results", []))
    return results


def _parse_json_response(content: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to find JSON block within the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {}


async def _load_brand_profile(tenant_id: str) -> dict:
    """Load tenant brand profile from DB (lightweight direct query)."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT coaching_niche, target_audience, tone_of_voice,
                       core_keywords, system_prompt_override
                FROM tenant_brand_profiles WHERE tenant_id = :tid
            """),
            {"tid": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else {}
