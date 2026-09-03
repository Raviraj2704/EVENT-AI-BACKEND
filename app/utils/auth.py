# ============================================================================
# Authentication Utilities
# ============================================================================
# File: app/utils/auth.py
# Purpose: JWT token handling, password hashing, security
# Status: Production-Ready ✅

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import logging

from app.config import settings


logger = logging.getLogger(__name__)


# ============================================================================
# PASSWORD HASHING
# ============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        bool: True if passwords match
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================================================
# JWT TOKEN HANDLING
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data
        expires_delta: Custom expiry duration
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        logger.info(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Payload data
        expires_delta: Custom expiry duration
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        logger.info(f"Refresh token created for user: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Token payload
    
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token without raising exception
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


# ============================================================================
# VERIFICATION CODE
# ============================================================================

import random
import string


def generate_verification_code() -> str:
    """
    Generate 6-digit verification code
    
    Returns:
        str: 6-digit code
    """
    return ''.join(random.choices(string.digits, k=6))


def verify_code_format(code: str) -> bool:
    """
    Verify code is 6 digits
    
    Args:
        code: Verification code
    
    Returns:
        bool: True if valid format
    """
    return len(code) == 6 and code.isdigit()


# ============================================================================
# RESET TOKEN
# ============================================================================

def create_password_reset_token(user_id: int) -> str:
    """
    Create password reset token (1 hour expiry)
    
    Args:
        user_id: User ID
    
    Returns:
        str: Reset token
    """
    data = {
        "sub": str(user_id),
        "type": "password_reset"
    }
    
    expire = datetime.utcnow() + timedelta(hours=1)
    data["exp"] = expire
    
    try:
        token = jwt.encode(
            data,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        logger.info(f"Password reset token created for user: {user_id}")
        return token
    except Exception as e:
        logger.error(f"Error creating reset token: {e}")
        raise


def verify_reset_token(token: str) -> Optional[int]:
    """
    Verify password reset token
    
    Args:
        token: Reset token
    
    Returns:
        int: User ID or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        if payload.get("type") != "password_reset":
            return None
        
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError:
        return None


# ============================================================================
# TOKEN PAIR
# ============================================================================

def create_token_pair(user_id: int) -> Dict[str, str]:
    """
    Create access and refresh token pair
    
    Args:
        user_id: User ID
    
    Returns:
        dict: {access_token, refresh_token}
    """
    access_token = create_access_token(
        data={"sub": str(user_id)}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user_id)}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }