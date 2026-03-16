"""
Authentication routes for OTP-based login
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
import logging

from models.user import (
    OTPRequest, OTPVerify, TokenResponse, UserResponse, User
)
from auth.otp_service import otp_service
from auth.jwt_service import jwt_service
from auth.dependencies import get_current_user
from database import mongodb

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(request: OTPRequest):
    """
    Request OTP for email authentication
    Generates and sends OTP to provided email
    """
    try:
        # Generate and store OTP (also sends it in development mode)
        otp_result = await otp_service.create_and_store_otp(request.email)

        note = (
            "OTP sent via email."
            if otp_result.get("email_sent")
            else otp_result.get("fallback_reason") or "OTP fallback to console logs."
        )
        
        return {
            "message": f"OTP sent to {request.email}",
            "expires_in_minutes": 5,
            "email_sent": bool(otp_result.get("email_sent")),
            "note": note,
        }
        
    except Exception as e:
        logger.error(f"Error requesting OTP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post("/verify-otp", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def verify_otp(request: OTPVerify):
    """
    Verify OTP and issue JWT token
    Creates user if doesn't exist (auto-registration)
    """
    try:
        # Verify OTP
        success, error_message = await otp_service.verify_otp(request.email, request.otp)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Check if user exists
        existing_user = await mongodb.users.find_one({"email": request.email})
        
        if existing_user:
            user_id = existing_user["user_id"]
            role = existing_user["role"]
            
            # Update verification status
            await mongodb.users.update_one(
                {"email": request.email},
                {
                    "$set": {
                        "is_verified": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"User {user_id} logged in successfully")
        else:
            # Create new user (auto-registration)
            user = User(
                email=request.email,
                is_verified=True,
                role="user"
            )
            
            await mongodb.users.insert_one(user.model_dump())
            user_id = user.user_id
            role = user.role
            
            logger.info(f"New user created: {user_id}")
        
        # Generate JWT token
        access_token = jwt_service.create_access_token(
            user_id=user_id,
            email=request.email,
            role=role
        )
        
        # Fetch updated user data
        user_doc = await mongodb.users.find_one({"user_id": user_id})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                user_id=user_doc["user_id"],
                email=user_doc["email"],
                role=user_doc["role"],
                is_verified=user_doc["is_verified"],
                created_at=user_doc["created_at"]
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again."
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    authorization: str = Depends(lambda: None),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Logout user by blacklisting JWT token
    """
    try:
        # Extract token and blacklist it
        if authorization:
            token = jwt_service.extract_token_from_header(authorization)
            if token:
                await jwt_service.blacklist_token(token)
        
        logger.info(f"User {current_user.user_id} logged out")
        
        return {
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        # Don't fail logout even if blacklisting fails
        return {
            "message": "Logged out successfully"
        }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return current_user
