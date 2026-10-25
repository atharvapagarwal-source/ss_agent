"""
Meta Graph API service (Instagram + Facebook).
Handles publishing, insights polling, DM dispatch, and comment replies.
"""
from __future__ import annotations
import httpx
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)
META_GRAPH_BASE = "https://graph.facebook.com/v21.0"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
async def publish_instagram(token: str, caption: str, carousel_urls: list[str]) -> dict:
    """Publish Instagram carousel post using the Content Publishing API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get IG Business Account ID
        me = await client.get(f"{META_GRAPH_BASE}/me", params={"access_token": token, "fields": "id"})
        me.raise_for_status()
        ig_user_id = me.json()["id"]

        if len(carousel_urls) > 1:
            # Create container for each slide
            children = []
            for url in carousel_urls:
                container = await client.post(
                    f"{META_GRAPH_BASE}/{ig_user_id}/media",
                    params={
                        "image_url": url,
                        "is_carousel_item": "true",
                        "access_token": token,
                    },
                )
                container.raise_for_status()
                children.append(container.json()["id"])

            # Create carousel container
            carousel = await client.post(
                f"{META_GRAPH_BASE}/{ig_user_id}/media",
                params={
                    "media_type": "CAROUSEL",
                    "children": ",".join(children),
                    "caption": caption[:2200],
                    "access_token": token,
                },
            )
            carousel.raise_for_status()
            container_id = carousel.json()["id"]
        else:
            # Single image post
            single = await client.post(
                f"{META_GRAPH_BASE}/{ig_user_id}/media",
                params={"image_url": carousel_urls[0] if carousel_urls else "", "caption": caption[:2200], "access_token": token},
            )
            single.raise_for_status()
            container_id = single.json()["id"]

        # Publish
        publish = await client.post(
            f"{META_GRAPH_BASE}/{ig_user_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
        publish.raise_for_status()
        result = publish.json()
        logger.info("Instagram post published", media_id=result.get("id"))
        return result


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
async def publish_facebook(token: str, post_text: str, page_id: Optional[str] = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        target = page_id or "me"
        resp = await client.post(
            f"{META_GRAPH_BASE}/{target}/feed",
            params={"message": post_text[:63206], "access_token": token},
        )
        resp.raise_for_status()
        return resp.json()


async def get_instagram_insights(token: str, media_id: str) -> dict:
    """Fetch IG media insights for Agent 5 telemetry."""
    fields = "impressions,reach,likes,comments_count,saved,video_views"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{META_GRAPH_BASE}/{media_id}/insights",
            params={"metric": fields, "access_token": token},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return {item["name"]: item["values"][0]["value"] for item in data}
        return {}


async def get_facebook_insights(token: str, post_id: str) -> dict:
    fields = "post_impressions,post_impressions_unique,post_reactions_like_total,post_comments"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{META_GRAPH_BASE}/{post_id}/insights",
            params={"metric": fields, "access_token": token},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return {item["name"]: item["values"][0]["value"] for item in data}
        return {}


async def send_dm(token: str, recipient_id: str, message: str, platform: str = "instagram") -> Optional[str]:
    """Send DM via Messenger/Instagram API."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/me/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": message[:1000]},
                "messaging_type": "RESPONSE",
            },
        )
        if resp.status_code == 200:
            return resp.json().get("message_id")
        logger.warning("Meta DM failed", status=resp.status_code, body=resp.text[:200])
        return None


async def post_comment_reply(token: str, comment_id: str, reply_text: str, platform: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/{comment_id}/replies",
            params={"message": reply_text[:500], "access_token": token},
        )
        return resp.json().get("id") if resp.status_code == 200 else None
