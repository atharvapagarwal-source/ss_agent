"""Auth and tenants routers — JWT auth + SuperAdmin tenant management."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from passlib.context import CryptContext
from jose import jwt
from config import settings
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    business_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    hashed = pwd_context.hash(body.password)
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    slug = body.business_name.lower().replace(" ", "-")[:50]
    await db.execute(text("""
        INSERT INTO users (id, email, hashed_password, full_name, role)
        VALUES (:id, :email, :hash, :name, 'coach')
    """), {"id": user_id, "email": body.email, "hash": hashed, "name": body.full_name})
    await db.execute(text("""
        INSERT INTO tenants (id, owner_id, business_name, slug, status, tier)
        VALUES (:id, :owner, :name, :slug, 'trial', 'starter')
    """), {"id": tenant_id, "owner": user_id, "name": body.business_name, "slug": slug})
    await db.commit()
    return {"user_id": user_id, "tenant_id": tenant_id, "status": "registered"}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT id, hashed_password, role FROM users WHERE email=:email"),
        {"email": body.email},
    )
    user = result.mappings().first()
    if not user or not pwd_context.verify(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get tenant_id
    tenant_result = await db.execute(
        text("SELECT id FROM tenants WHERE owner_id=:uid LIMIT 1"),
        {"uid": str(user["id"])},
    )
    tenant = tenant_result.mappings().first()

    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "tenant_id": str(tenant["id"]) if tenant else None,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
