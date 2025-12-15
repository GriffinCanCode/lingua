"""Security Module with Monadic Error Handling

Handles authentication, token management, and password hashing
using Result types for predictable error propagation.
"""
from datetime import datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from core.config import settings
from core.logging import auth_logger
from core.errors import (
    AppError,
    ErrorCode,
    Ok,
    Err,
    Result,
    token_expired,
    token_invalid,
    token_missing,
    raise_error,
)

log = auth_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    user_id = data.get("sub", "unknown")
    log.info("token_created", user_id=user_id, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Result[dict, AppError]:
    """Decode and validate JWT token.
    
    Returns:
        Ok(payload) on success
        Err(AppError) on failure with specific error code
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return Ok(payload)
    except ExpiredSignatureError:
        log.warning("token_expired")
        return token_expired(origin="security.decode_token")
    except JWTError as e:
        log.warning("token_invalid", error=str(e))
        return token_invalid(str(e), origin="security.decode_token")


def validate_token(token: str) -> Result[str, AppError]:
    """Validate token and extract user ID.
    
    Returns:
        Ok(user_id) on success
        Err(AppError) on failure
    """
    result = decode_token(token)
    
    match result:
        case Ok(payload):
            user_id = payload.get("sub")
            if not user_id:
                log.warning("token_invalid", reason="missing_user_id")
                return token_invalid("missing user ID", origin="security.validate_token")
            log.debug("token_validated", user_id=user_id)
            return Ok(user_id)
        case Err(error):
            return Err(error)


async def get_current_user_id(token: str | None = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency to get current user ID from token.
    
    Raises AppErrorException if token is invalid, allowing
    the exception handler to return proper error response.
    """
    if token is None:
        raise_error(token_missing(origin="security.get_current_user_id").error)
    
    result = validate_token(token)
    
    match result:
        case Ok(user_id):
            return user_id
        case Err(error):
            raise_error(error)


def get_optional_user_id(token: str | None = Depends(oauth2_scheme)) -> str | None:
    """FastAPI dependency to optionally get user ID.
    
    Returns None if no token provided, raises on invalid token.
    """
    if token is None:
        return None
    
    result = validate_token(token)
    
    match result:
        case Ok(user_id):
            return user_id
        case Err(error):
            raise_error(error)
