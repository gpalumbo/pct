"""Auth router — /api/auth endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from pct.auth.dependencies import get_current_user, get_settings
from pct.auth.models import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from pct.auth.service import authenticate_user, register_user
from pct.config import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, settings: Settings = Depends(get_settings)):
    if not register_user(req.email, req.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    from pct.auth.service import create_token

    token = create_token(req.email, settings.secret_key, settings.jwt_algorithm, settings.jwt_expire_minutes)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, settings: Settings = Depends(get_settings)):
    if not authenticate_user(req.email, req.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    from pct.auth.service import create_token

    token = create_token(req.email, settings.secret_key, settings.jwt_algorithm, settings.jwt_expire_minutes)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(email: str = Depends(get_current_user)):
    return UserResponse(email=email)
