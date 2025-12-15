"""Authentication API with Monadic Error Handling

Handles user registration, login, and token management
using Result types for predictable error propagation.
"""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, fetch_one
from core.config import settings
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_id,
)
from core.errors import (
    Ok,
    Err,
    invalid_credentials,
    duplicate_key,
    not_found,
    raise_error,
    raise_result,
)
from models.user import User

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    native_language: str = "en"
    target_language: str = "ru"


class UserResponse(BaseModel):
    id: UUID
    email: str
    native_language: str
    target_language: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise_error(duplicate_key("User", "email", user_data.email, origin="api.auth.register").error)
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        native_language=user_data.native_language,
        target_language=user_data.target_language,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return access token."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise_error(invalid_credentials(origin="api.auth.login").error)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user."""
    result = await fetch_one(db, User, UUID(user_id), "User")
    raise_result(result)
    return result.unwrap()
