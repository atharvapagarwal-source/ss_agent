"""
OAuth Token Vault — store and retrieve encrypted platform tokens.
All reads are logged to audit.token_access_log.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import text
from services.encryption import encrypt_token, decrypt_token
import structlog

logger = structlog.get_logger(__name__)


async def store_token(
    tenant_id: str,
    platform: str,
    access_token: str,
    refresh_token: Optional[str],
    platform_user_id: str,
    platform_page_id: Optional[str],
    scopes: list[str],
    expires_at: Optional[datetime],
) -> None:
    """Encrypt and upsert an OAuth token into the vault schema."""
    from database import AsyncSessionLocal

    enc_access, iv_access, tag_access = encrypt_token(access_token)
    enc_refresh, iv_refresh, tag_refresh = (None, None, None)
    if refresh_token:
        enc_refresh, iv_refresh, tag_refresh = encrypt_token(refresh_token)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO vault.oauth_tokens (
                    tenant_id, platform,
                    encrypted_access_token, encrypted_refresh_token,
                    encryption_iv, encryption_tag,
                    platform_user_id, platform_page_id,
                    scopes_granted, token_expires_at, is_active, last_refreshed_at
                ) VALUES (
                    :tid, :platform,
                    :enc_access, :enc_refresh,
                    :iv, :tag,
                    :user_id, :page_id,
                    :scopes, :expires_at, TRUE, NOW()
                )
                ON CONFLICT (tenant_id, platform, platform_user_id) DO UPDATE SET
                    encrypted_access_token = EXCLUDED.encrypted_access_token,
                    encrypted_refresh_token = COALESCE(EXCLUDED.encrypted_refresh_token, vault.oauth_tokens.encrypted_refresh_token),
                    encryption_iv = EXCLUDED.encryption_iv,
                    encryption_tag = EXCLUDED.encryption_tag,
                    token_expires_at = EXCLUDED.token_expires_at,
                    last_refreshed_at = NOW(),
                    is_active = TRUE
            """),
            {
                "tid": tenant_id,
                "platform": platform,
                "enc_access": enc_access,
                "enc_refresh": enc_refresh,
                "iv": iv_access,
                "tag": tag_access,
                "user_id": platform_user_id,
                "page_id": platform_page_id,
                "scopes": scopes,
                "expires_at": expires_at,
            },
        )
        # Audit log
        await session.execute(
            text("""
                INSERT INTO audit.token_access_log (tenant_id, platform, accessed_by, action)
                VALUES (:tid, :platform, 'oauth_vault_store', 'write')
            """),
            {"tid": tenant_id, "platform": platform},
        )
        await session.commit()

    logger.info("OAuth token stored", tenant_id=tenant_id, platform=platform)


async def get_decrypted_token(tenant_id: str, platform: str, caller: str = "agent") -> str:
    """
    Retrieve and decrypt the active access token for a tenant+platform.
    Raises ValueError if no active token found.
    """
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT encrypted_access_token, encryption_iv, encryption_tag, token_expires_at
                FROM vault.oauth_tokens
                WHERE tenant_id = :tid AND platform = :platform AND is_active = TRUE
                ORDER BY last_refreshed_at DESC
                LIMIT 1
            """),
            {"tid": tenant_id, "platform": platform},
        )
        row = result.mappings().first()

        if not row:
            raise ValueError(f"No active OAuth token for tenant={tenant_id} platform={platform}")

        # Audit log
        await session.execute(
            text("""
                INSERT INTO audit.token_access_log (tenant_id, platform, accessed_by, action)
                VALUES (:tid, :platform, :caller, 'read')
            """),
            {"tid": tenant_id, "platform": platform, "caller": caller},
        )
        await session.commit()

    decrypted = decrypt_token(
        ciphertext=bytes(row["encrypted_access_token"]),
        iv=bytes(row["encryption_iv"]),
        tag=bytes(row["encryption_tag"]),
    )

    # Check token expiry (log warning, let caller handle refresh)
    expires_at = row.get("token_expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        logger.warning("OAuth token may be expired", tenant_id=tenant_id, platform=platform)

    return decrypted


async def revoke_token(tenant_id: str, platform: str) -> None:
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE vault.oauth_tokens SET is_active=FALSE WHERE tenant_id=:tid AND platform=:pl"),
            {"tid": tenant_id, "pl": platform},
        )
        await session.execute(
            text("""
                INSERT INTO audit.token_access_log (tenant_id, platform, accessed_by, action)
                VALUES (:tid, :platform, 'oauth_vault_revoke', 'revoke')
            """),
            {"tid": tenant_id, "platform": platform},
        )
        await session.commit()
    logger.info("OAuth token revoked", tenant_id=tenant_id, platform=platform)
