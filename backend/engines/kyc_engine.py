"""
KYC Engine - Verification, encryption, and masking of PII
"""

import re
import random
import logging
from cryptography.fernet import Fernet
from typing import Tuple, Optional

from config import settings

logger = logging.getLogger(__name__)


class KYCEngine:
    """
    KYC verification engine
    - Validates Aadhaar and PAN format
    - Encrypts PII for storage
    - Masks sensitive data for LLM/logs
    - Simulates verification with 90% success rate
    """
    
    def __init__(self):
        # Initialize encryption cipher
        if not settings.ENCRYPTION_KEY:
            logger.warning("ENCRYPTION_KEY not set! Using temporary key for development.")
            self.cipher = Fernet(Fernet.generate_key())
        else:
            self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    
    @staticmethod
    def validate_aadhaar_format(aadhaar: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Aadhaar number format
        Must be 12 digits
        """
        # Remove spaces and hyphens
        aadhaar_clean = re.sub(r'[\s-]', '', aadhaar)
        
        if not aadhaar_clean.isdigit():
            return False, "Aadhaar must contain only digits"
        
        if len(aadhaar_clean) != 12:
            return False, f"Aadhaar must be 12 digits, got {len(aadhaar_clean)}"
        
        return True, None
    
    @staticmethod
    def validate_pan_format(pan: str) -> Tuple[bool, Optional[str]]:
        """
        Validate PAN format
        Format: AAAAA9999A (5 letters, 4 digits, 1 letter)
        """
        pan_clean = pan.upper().strip()
        
        # PAN regex pattern
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        
        if not re.match(pan_pattern, pan_clean):
            return False, "Invalid PAN format. Expected: AAAAA9999A"
        
        return True, None
    
    def encrypt_pii(self, data: str) -> str:
        """Encrypt sensitive PII data"""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt sensitive PII data"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    @staticmethod
    def mask_aadhaar(aadhaar: str) -> str:
        """
        Mask Aadhaar for display/logging
        Shows only last 4 digits: XXXX-XXXX-1234
        """
        aadhaar_clean = re.sub(r'[\s-]', '', aadhaar)
        if len(aadhaar_clean) < 4:
            return "XXXX-XXXX-XXXX"
        
        last_4 = aadhaar_clean[-4:]
        return f"XXXX-XXXX-{last_4}"
    
    @staticmethod
    def mask_pan(pan: str) -> str:
        """
        Mask PAN for display/logging
        Shows first 2 and last 3: AB***8901K
        """
        pan_clean = pan.upper().strip()
        if len(pan_clean) < 5:
            return "XX***XXXXX"
        
        first_2 = pan_clean[:2]
        last_3 = pan_clean[-3:]
        return f"{first_2}***{last_3}"
    
    def verify_aadhaar(self, aadhaar: str) -> Tuple[bool, dict]:
        """
        Simulate Aadhaar verification
        Deterministic success for valid format in mock mode
        """
        # Validate format
        is_valid, error = self.validate_aadhaar_format(aadhaar)
        if not is_valid:
            return False, {
                "status": "FAILED",
                "reason": error,
                "masked": "XXXX-XXXX-XXXX"
            }
        
        return True, {
            "status": "VERIFIED",
            "provider": "UIDAI_MOCK",
            "masked": self.mask_aadhaar(aadhaar),
            "verification_id": f"AADHAAR-{random.randint(100000, 999999)}"
        }
    
    def verify_pan(self, pan: str) -> Tuple[bool, dict]:
        """
        Simulate PAN verification
        Deterministic success for valid format in mock mode
        """
        # Validate format
        is_valid, error = self.validate_pan_format(pan)
        if not is_valid:
            return False, {
                "status": "FAILED",
                "reason": error,
                "masked": "XX***XXXXX"
            }
        
        return True, {
            "status": "VERIFIED",
            "provider": "PAN_MOCK",
            "masked": self.mask_pan(pan),
            "verification_id": f"PAN-{random.randint(100000, 999999)}"
        }
    
    def process_kyc(self, aadhaar: str, pan: str, user_id: str = None) -> dict:
        """
        Complete KYC processing
        Validates, verifies, encrypts, and returns masked data
        """
        result = {
            "kyc_status": "PENDING",
            "aadhaar": {},
            "pan": {},
            "encrypted_aadhaar": None,
            "encrypted_pan": None,
            "verification_id": None
        }
        
        # Verify Aadhaar
        aadhaar_success, aadhaar_data = self.verify_aadhaar(aadhaar)
        result["aadhaar"] = aadhaar_data
        
        if not aadhaar_success:
            result["kyc_status"] = "FAILED"
            result["reason"] = aadhaar_data.get("reason")
            return result
        
        # Verify PAN
        pan_success, pan_data = self.verify_pan(pan)
        result["pan"] = pan_data
        
        if not pan_success:
            result["kyc_status"] = "FAILED"
            result["reason"] = pan_data.get("reason")
            return result
        
        # Both verified - encrypt for storage
        try:
            result["encrypted_aadhaar"] = self.encrypt_pii(aadhaar)
            result["encrypted_pan"] = self.encrypt_pii(pan.upper())
            result["kyc_status"] = "VERIFIED"
            result["verification_id"] = f"KYC-{random.randint(100000, 999999)}"
            
            logger.info(f"KYC verification successful: {result['verification_id']}")
            
        except Exception as e:
            logger.error(f"KYC encryption failed: {e}")
            result["kyc_status"] = "FAILED"
            result["reason"] = "Internal error during verification"
        
        return result


# Global instance
kyc_engine = KYCEngine()
