"""
OTP Service for email-based authentication
Generates, stores, and verifies OTPs using Redis
"""

import random
import string
import logging
from passlib.hash import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from database import redis_client
from config import settings
from services.email_service import email_service

logger = logging.getLogger(__name__)


class OTPService:
    """OTP generation and verification service"""
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random numeric OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def hash_otp(otp: str) -> str:
        """Hash OTP using bcrypt"""
        return bcrypt.hash(otp)
    
    @staticmethod
    def verify_otp_hash(otp: str, hashed: str) -> bool:
        """Verify OTP against hash"""
        try:
            return bcrypt.verify(otp, hashed)
        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return False
    
    @staticmethod
    async def create_and_store_otp(email: str) -> Dict[str, Any]:
        """
        Generate OTP, hash it, store in Redis
        Returns: The plain OTP (to be sent to user)
        """
        # Generate OTP
        otp = OTPService.generate_otp()
        
        # Store plain OTP in Redis (for development - in production use hashing)
        expiry_seconds = settings.OTP_EXPIRY_MINUTES * 60
        
        # Store directly without hashing for development
        key = f"otp:{email}"
        data = {
            "otp": otp,  # Store plain OTP
            "attempts": "0"
        }
        await redis_client.client.hset(key, mapping=data)
        await redis_client.client.expire(key, expiry_seconds)
        
        logger.info(f"OTP generated for {email} (expires in {settings.OTP_EXPIRY_MINUTES} minutes)")

        email_sent = await email_service.send_otp_email(
            to_email=email,
            otp=otp,
            expiry_minutes=settings.OTP_EXPIRY_MINUTES,
        )

        fallback_reason = None
        if not email_sent:
            provider = email_service.active_provider
            if provider == "resend":
                fallback_reason = "Resend API send failed. Check backend logs for detailed error."
            elif provider == "smtp":
                fallback_reason = "SMTP send failed. Check backend logs for detailed SMTP error."
            elif not email_service.is_configured:
                fallback_reason = (
                    "Email provider not configured. Missing: "
                    + ", ".join(email_service.missing_config_fields())
                )
            else:
                fallback_reason = "Email send failed. Check backend logs for details."

        # Fallback: keep console simulation when SMTP is not configured/failed
        if not email_sent:
            logger.info("=" * 60)
            logger.info("📧 OTP EMAIL SIMULATION")
            logger.info("=" * 60)
            logger.info(f"To: {email}")
            logger.info(f"Subject: Your NBFC Loan Platform OTP")
            logger.info("-" * 60)
            logger.info(f"Your OTP is: {otp}")
            logger.info(f"Valid for: {settings.OTP_EXPIRY_MINUTES} minutes")
            logger.info(f"Do not share this OTP with anyone.")
            logger.info("=" * 60)
        
        return {
            "otp": otp,
            "email_sent": email_sent,
            "fallback_reason": fallback_reason,
        }
    
    @staticmethod
    async def verify_otp(email: str, otp: str) -> Tuple[bool, Optional[str]]:
        """
        Verify OTP for an email
        Returns: (success: bool, error_message: Optional[str])
        """
        # Get stored OTP data from Redis
        otp_data = await redis_client.get_otp(email)
        
        if not otp_data:
            return False, "OTP expired or not found. Please request a new OTP."
        
        # Check attempts
        attempts = int(otp_data.get("attempts", 0))
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            await redis_client.delete_otp(email)
            return False, f"Maximum {settings.OTP_MAX_ATTEMPTS} attempts exceeded. Please request a new OTP."
        
        # Verify OTP (direct comparison for development)
        stored_otp = otp_data.get("otp")
        if not stored_otp or stored_otp != otp:
            # Increment attempts
            await redis_client.increment_otp_attempts(email)
            remaining = settings.OTP_MAX_ATTEMPTS - attempts - 1
            return False, f"Invalid OTP. {remaining} attempts remaining."
        
        # Success - delete OTP from Redis
        await redis_client.delete_otp(email)
        logger.info(f"OTP verified successfully for {email}")
        
        return True, None


# Global instance
otp_service = OTPService()
