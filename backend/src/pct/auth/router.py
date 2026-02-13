"""Auth API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from pct import config
from pct.auth.dependencies import get_current_user
from pct.auth.models import (
    GoogleAuthRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from pct.auth.service import (
    create_access_token,
    create_user,
    get_user,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = get_user(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed = hash_password(user_data.password)
    create_user(user_data.email, hashed, auth_provider="local")
    token = create_access_token({"sub": user_data.email})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = get_user(user_data.email)
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token({"sub": user_data.email})
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
async def google_auth(data: GoogleAuthRequest):
    if not config.settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google auth not configured",
        )
    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        idinfo = id_token.verify_oauth2_token(
            data.credential, requests.Request(), config.settings.google_client_id
        )
        email = idinfo["email"]
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        ) from err

    user = get_user(email)
    if not user:
        create_user(email, hashed_password="", auth_provider="google")
    token = create_access_token({"sub": email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        email=current_user["email"],
        auth_provider=current_user["auth_provider"],
    )
