"""
FastAPI dependencies for authentication and authorization
"""

from fastapi import Depends, HTTPException, status, Header
from typing import Optional, Literal
import logging

from auth.jwt_service import jwt_service
from database import mongodb
from models.user import User, UserResponse

logger = logging.getLogger(__name__)


async def get_current_user(authorization: Optional[str] = Header(None)) -> UserResponse:
    """
    FastAPI dependency to get current authenticated user
    Validates JWT token and returns user data
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token
    token = jwt_service.extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    payload = await jwt_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Fetch user from database
    user_doc = await mongodb.users.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return UserResponse(
        user_id=user_doc["user_id"],
        email=user_doc["email"],
        role=user_doc["role"],
        is_verified=user_doc["is_verified"],
        created_at=user_doc["created_at"]
    )


def require_role(required_role: Literal["user", "admin"]):
    """
    Dependency factory for role-based access control
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if required_role == "admin" and current_user.role != "admin":
            logger.warning(f"Unauthorized admin access attempt by user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Admin access required.",
            )
        return current_user
    
    return role_checker


# Optional user dependency (doesn't raise error if no token)
async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[UserResponse]:
    """
    Get current user if authenticated, None otherwise
    Useful for endpoints that work differently for authenticated vs anonymous users
    """
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
