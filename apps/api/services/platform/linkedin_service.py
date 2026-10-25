"""LinkedIn API v2 service — publishing, stats, DMs, and comment replies."""
from __future__ import annotations
import httpx
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)
LI_BASE = "https://api.linkedin.com/v2"
LI_REST = "https://api.linkedin.com/rest"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202410",
        "Content-Type": "application/json",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
async def publish_post(token: str, text_post: str, pdf_url: Optional[str] = None) -> dict:
    """Publish a LinkedIn text post or document (carousel PDF)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get author URN
        me = await client.get(f"{LI_BASE}/me", headers=_headers(token))
        me.raise_for_status()
        author_urn = f"urn:li:person:{me.json()['id']}"

        if pdf_url:
            # Upload document (carousel PDF) first
            register_resp = await client.post(
                f"{LI_REST}/documents",
                headers=_headers(token),
                json={
                    "initializeUploadRequest": {
                        "owner": author_urn,
                    }
                },
            )
            register_resp.raise_for_status()
            upload_data = register_resp.json()
            upload_url = upload_data["value"]["uploadUrl"]
            document_urn = upload_data["value"]["document"]

            # Upload the PDF bytes
            pdf_resp = await client.get(pdf_url, follow_redirects=True)
            pdf_resp.raise_for_status()
            await client.put(upload_url, content=pdf_resp.content, headers={"Content-Type": "application/pdf"})

            # Create post with document
            post_body = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text_post[:3000]},
                        "shareMediaCategory": "DOCUMENT",
                        "media": [{"status": "READY", "media": document_urn}],
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
        else:
            post_body = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text_post[:3000]},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

        resp = await client.post(f"{LI_BASE}/ugcPosts", headers=_headers(token), json=post_body)
        resp.raise_for_status()
        post_urn = resp.headers.get("X-RestLi-Id", "")
        logger.info("LinkedIn post published", urn=post_urn)
        return {"id": post_urn}


async def get_share_statistics(token: str, share_urn: str) -> dict:
    """Fetch LinkedIn post analytics for Agent 5."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{LI_REST}/organizationalEntityShareStatistics",
            headers=_headers(token),
            params={"q": "organizationalEntity", "shares[0]": share_urn},
        )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [{}])
            return elements[0].get("totalShareStatistics", {}) if elements else {}
        return {}


async def send_dm(token: str, recipient_urn: str, message: str) -> Optional[str]:
    """Send a LinkedIn message (InMail / direct message)."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Get sender URN
        me = await client.get(f"{LI_BASE}/me", headers=_headers(token))
        sender_urn = f"urn:li:person:{me.json()['id']}"

        resp = await client.post(
            f"{LI_BASE}/messages",
            headers=_headers(token),
            json={
                "recipients": [recipient_urn],
                "subject": "",
                "body": message[:8000],
                "messageType": "MEMBER_TO_MEMBER",
                "sender": sender_urn,
            },
        )
        return resp.headers.get("x-restli-id") if resp.status_code in (200, 201) else None


async def post_comment_reply(token: str, comment_urn: str, reply_text: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{LI_BASE}/socialActions/{comment_urn}/comments",
            headers=_headers(token),
            json={"message": {"text": reply_text[:1250]}},
        )
        return resp.json().get("id") if resp.status_code in (200, 201) else None
