"""
JWT Service for token generation and verification
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import logging
from uuid import uuid4

from config import settings
from database import redis_client

logger = logging.getLogger(__name__)


class JWTService:
    """JWT token management service"""
    
    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        role: str = "user",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=settings.JWT_EXPIRY_HOURS)
        
        expire = datetime.utcnow() + expires_delta
        token_id = str(uuid4())
        
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": token_id  # JWT ID for blacklisting
        }
        
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info(f"JWT token created for user {user_id} (expires: {expire})")
        
        return encoded_jwt
    
    @staticmethod
    async def verify_token(token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        Returns payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check if token is blacklisted
            token_id = payload.get("jti")
            if token_id:
                is_blacklisted = await redis_client.is_token_blacklisted(token_id)
                if is_blacklisted:
                    logger.warning(f"Attempted use of blacklisted token: {token_id}")
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidSignatureError as e:
            logger.error(f"Invalid token signature: {e}")
            return None
        except jwt.DecodeError as e:
            logger.error(f"Token decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return None
    
    @staticmethod
    async def blacklist_token(token: str):
        """
        Add token to blacklist (for logout)
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False}  # Decode even if expired
            )
            
            token_id = payload.get("jti")
            if token_id:
                # Calculate remaining TTL
                exp = payload.get("exp")
                if exp:
                    exp_datetime = datetime.fromtimestamp(exp)
                    remaining = int((exp_datetime - datetime.utcnow()).total_seconds())
                    if remaining > 0:
                        await redis_client.blacklist_token(token_id, remaining)
                        logger.info(f"Token {token_id} blacklisted")
                    else:
                        logger.info(f"Token {token_id} already expired, not blacklisting")
                        
        except jwt.JWTError as e:
            logger.error(f"Error blacklisting token: {e}")
    
    @staticmethod
    def extract_token_from_header(authorization: str) -> Optional[str]:
        """
        Extract token from Authorization header
        Expected format: "Bearer <token>"
        """
        if not authorization:
            return None
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]


# Global instance
jwt_service = JWTService()
