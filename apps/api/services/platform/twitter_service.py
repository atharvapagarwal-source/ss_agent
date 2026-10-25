"""X (Twitter) API v2 service — thread publishing, metrics, DMs, and replies."""
from __future__ import annotations
import httpx
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)
TW_BASE = "https://api.twitter.com/2"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _oauth_headers(access_token: str) -> dict:
    """For user-context endpoints (DMs, posting) that require OAuth 1.0a or OAuth 2.0 user token."""
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
async def publish_thread(token: str, tweets: list[str]) -> dict:
    """
    Publish a multi-tweet thread.
    Each tweet replies to the previous one to form the thread chain.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        last_tweet_id = None
        first_tweet_id = None

        for i, tweet_text in enumerate(tweets):
            payload: dict = {"text": tweet_text[:280]}
            if last_tweet_id:
                payload["reply"] = {"in_reply_to_tweet_id": last_tweet_id}

            resp = await client.post(f"{TW_BASE}/tweets", headers=_oauth_headers(token), json=payload)
            resp.raise_for_status()
            tweet_id = resp.json()["data"]["id"]

            if i == 0:
                first_tweet_id = tweet_id
            last_tweet_id = tweet_id

        logger.info("Twitter thread published", first_tweet_id=first_tweet_id, tweets=len(tweets))
        return {"id": first_tweet_id}


async def get_tweet_metrics(token: str, tweet_id: str) -> dict:
    """Fetch tweet public + non-public metrics for Agent 5 telemetry."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{TW_BASE}/tweets/{tweet_id}",
            headers=_headers(token),
            params={
                "tweet.fields": "public_metrics,non_public_metrics,organic_metrics",
            },
        )
        if resp.status_code == 200:
            return resp.json().get("data", {})
        return {}


async def send_dm(token: str, recipient_id: str, message: str) -> Optional[str]:
    """Send a DM via Twitter API v2 Direct Messages."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{TW_BASE}/dm_conversations/with/{recipient_id}/messages",
            headers=_oauth_headers(token),
            json={"text": message[:10000]},
        )
        if resp.status_code in (200, 201):
            return resp.json().get("data", {}).get("dm_event_id")
        logger.warning("Twitter DM failed", status=resp.status_code)
        return None


async def reply_to_tweet(token: str, tweet_id: str, reply_text: str) -> Optional[str]:
    """Post a reply to a tweet (for public comment-trigger replies)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TW_BASE}/tweets",
            headers=_oauth_headers(token),
            json={"text": reply_text[:280], "reply": {"in_reply_to_tweet_id": tweet_id}},
        )
        return resp.json().get("data", {}).get("id") if resp.status_code in (200, 201) else None
