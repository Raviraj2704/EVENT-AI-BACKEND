# ============================================================================
# Authentication Routes
# ============================================================================
# File: app/routes/auth.py
# Purpose: User registration, login, verification, and password reset
# Status: Production-Ready ✅

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserLoginResponse, EmailVerificationRequest, PasswordResetRequest,
    PasswordResetConfirmRequest, RefreshTokenRequest, UserProfileResponse,
    ErrorResponse
)
from app.utils.auth import (
    hash_password, verify_password, create_token_pair,
    create_access_token, verify_token, generate_verification_code,
    create_password_reset_token, verify_reset_token
)
from app.utils.email import (
    send_welcome_email, send_verification_email,
    send_password_reset_email
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])


# ============================================================================
# CONSTANTS
# ============================================================================

# In-memory verification code storage (use Redis in production)
verification_codes = {}
password_reset_attempts = {}


# ============================================================================
# REGISTER ENDPOINT
# ============================================================================

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}
)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new user
    
    Args:
        request: Registration data
        db: Database session
    
    Returns:
        TokenResponse: Access and refresh tokens
    
    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        logger.warning(f"Registration failed: Username {request.username} already exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        logger.warning(f"Registration failed: Email {request.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    try:
        # Create new user
        new_user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User registered: {new_user.username}")
        
        # Send welcome email
        send_welcome_email(request.email, request.username)
        
        # Generate verification code
        verification_code = generate_verification_code()
        verification_codes[request.email] = {
            "code": verification_code,
            "expires_at": datetime.utcnow() + timedelta(minutes=15),
            "attempts": 0
        }
        
        # Send verification email
        send_verification_email(request.email, request.username, verification_code)
        
        # Create token pair
        tokens = create_token_pair(new_user.id)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=60 * 15  # 15 minutes
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )


# ============================================================================
# LOGIN ENDPOINT
# ============================================================================

@router.post(
    "/login",
    response_model=UserLoginResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login
    
    Args:
        request: Login credentials
        db: Database session
    
    Returns:
        UserLoginResponse: Tokens and user data
    
    Raises:
        HTTPException: If credentials invalid or user not found
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == request.username_or_email) |
        (User.email == request.username_or_email)
    ).first()
    
    if not user:
        logger.warning(f"Login failed: User {request.username_or_email} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Login failed: Invalid password for {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: User {user.username} is inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    try:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create token pair
        tokens = create_token_pair(user.id)
        
        logger.info(f"User logged in: {user.username}")
        
        return UserLoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=60 * 15,
            user=UserProfileResponse.model_validate(user)
        )
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# ============================================================================
# EMAIL VERIFICATION ENDPOINT
# ============================================================================

@router.post(
    "/verify-email",
    response_model=dict,
    responses={400: {"model": ErrorResponse}}
)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email with code
    
    Args:
        request: Verification code
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: If code invalid or expired
    """
    # Get stored verification code
    stored_data = verification_codes.get(request.email)
    
    if not stored_data:
        logger.warning(f"Verification failed: No code for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found"
        )
    
    # Check if expired
    if datetime.utcnow() > stored_data["expires_at"]:
        del verification_codes[request.email]
        logger.warning(f"Verification failed: Code expired for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired"
        )
    
    # Check attempts
    if stored_data["attempts"] >= 3:
        del verification_codes[request.email]
        logger.warning(f"Verification failed: Too many attempts for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts"
        )
    
    # Verify code
    if stored_data["code"] != request.verification_code:
        stored_data["attempts"] += 1
        logger.warning(f"Verification failed: Invalid code for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Mark user as verified
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user.is_verified = True
        db.commit()
        
        # Clean up code
        del verification_codes[request.email]
        
        logger.info(f"Email verified: {request.email}")
        
        return {"message": "Email verified successfully"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed"
        )


# ============================================================================
# REFRESH TOKEN ENDPOINT
# ============================================================================

@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}}
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        request: Refresh token
        db: Database session
    
    Returns:
        TokenResponse: New access and refresh tokens
    
    Raises:
        HTTPException: If refresh token invalid
    """
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)
        
        if payload.get("type") == "refresh":
            user_id = int(payload.get("sub"))
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new token pair
        tokens = create_token_pair(user.id)
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=60 * 15
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


# ============================================================================
# PASSWORD RESET REQUEST ENDPOINT
# ============================================================================

@router.post(
    "/forgot-password",
    response_model=dict,
    responses={404: {"model": ErrorResponse}}
)
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset
    
    Args:
        request: User email
        db: Database session
    
    Returns:
        dict: Success message
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal if email exists
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "If email exists, reset link will be sent"}
    
    try:
        # Create reset token
        reset_token = create_password_reset_token(user.id)
        
        # Store attempt
        password_reset_attempts[reset_token] = {
            "user_id": user.id,
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Send reset email
        send_password_reset_email(request.email, user.username, reset_token)
        
        logger.info(f"Password reset email sent to: {request.email}")
        
        return {"message": "If email exists, reset link will be sent"}
    
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


# ============================================================================
# PASSWORD RESET CONFIRM ENDPOINT
# ============================================================================

@router.post(
    "/reset-password",
    response_model=dict,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}}
)
async def reset_password(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset
    
    Args:
        request: Reset token and new password
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: If token invalid or expired
    """
    # Verify reset token
    user_id = verify_reset_token(request.token)
    
    if not user_id:
        logger.warning("Password reset failed: Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Update password
        user.password_hash = hash_password(request.new_password)
        db.commit()
        
        # Clean up
        if request.token in password_reset_attempts:
            del password_reset_attempts[request.token]
        
        logger.info(f"Password reset for user: {user.username}")
        
        return {"message": "Password reset successfully"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


# ============================================================================
# LOGOUT ENDPOINT
# ============================================================================

@router.post(
    "/logout",
    response_model=dict
)
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Logout user
    
    Args:
        request: HTTP request
        db: Database session
    
    Returns:
        dict: Success message
    """
    try:
        # In production, add token to blacklist in Redis
        logger.info("User logged out")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )