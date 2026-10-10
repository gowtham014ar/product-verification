from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from common.logging.logger import get_logger

router = APIRouter()
log    = get_logger("auth-service")


# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "customer"
    wallet_address: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v.split("@")[0]) == 0 or len(v.split("@")[1]) == 0:
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v.split("@")[0]) == 0 or len(v.split("@")[1]) == 0:
            raise ValueError("Invalid email format")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    wallet_address: str | None
    is_active: bool


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        wallet_address=body.wallet_address,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("user registered", extra={"event": "user_registered", "user_id": user.id, "role": user.role})
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        log.warning("login failed", extra={"event": "login_failed", "email": body.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(subject=user.id, role=user.role)
    log.info("user logged in", extra={"event": "login_success", "user_id": user.id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@router.get("/me", response_model=UserResponse)
async def me(
    current: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, current["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/verify-token")
async def verify_token(current: dict = Depends(get_current_user)):
    """Internal endpoint called by api-gateway to validate tokens."""
    return {"valid": True, "user_id": current["sub"], "role": current["role"]}
