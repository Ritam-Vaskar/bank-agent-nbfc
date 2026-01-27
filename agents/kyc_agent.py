"""
KYC Verification Agent

Use mock Aadhaar & PAN APIs.
Rules:
- Mask PII
- Never store raw IDs
- Hash identifiers
- Simulate OTP flow
"""

import re
import hashlib
import random
from typing import Dict, Any
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_services.aadhaar_api import verify_aadhaar
from mock_services.pan_api import verify_pan

class KYCAgent:
    def __init__(self):
        self.pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
        self.aadhaar_pattern = r'^\d{12}$'
    
    def mask_pan(self, pan: str) -> str:
        """Mask PAN: ABCDE1234F -> XXXXX1234X"""
        if len(pan) != 10:
            return 'INVALID'
        return f"XXXXX{pan[5:9]}X"
    
    def mask_aadhaar(self, aadhaar: str) -> str:
        """Mask Aadhaar: 123456789012 -> XXXX-XXXX-9012"""
        if len(aadhaar) != 12:
            return 'INVALID'
        return f"XXXX-XXXX-{aadhaar[-4:]}"
    
    def hash_identifier(self, identifier: str) -> str:
        """Hash identifier for secure storage"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def process(self, user_message: str, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify KYC details
        Returns verification status and masked data
        """
        
        # Extract PAN
        pan_match = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', user_message.upper())
        
        if pan_match:
            pan = pan_match[0]
            
            # Verify PAN using mock service
            pan_result = verify_pan(pan)
            
            if not pan_result['valid']:
                return {
                    'kyc_status': 'FAILED',
                    'flags': ['Invalid PAN'],
                    'masked_data': {},
                    'reply': 'The PAN number provided is invalid. Please check and provide a valid PAN.'
                }
            
            # Now ask for Aadhaar if not provided
            if 'aadhaar_verified' not in loan_data:
                # Generate OTP (mock)
                otp = random.randint(100000, 999999)
                
                return {
                    'kyc_status': 'PENDING',
                    'flags': [],
                    'masked_data': {
                        'pan': self.mask_pan(pan),
                        'pan_hash': self.hash_identifier(pan),
                        'pan_name': pan_result.get('name', 'Unknown')
                    },
                    'reply': f"""✅ PAN verified successfully!
Name as per PAN: {pan_result.get('name', 'Unknown')}

Now, please provide your 12-digit Aadhaar number for final verification.""",
                    'temp_otp': otp  # In production, send via SMS
                }
        
        # Extract Aadhaar
        aadhaar_match = re.findall(r'\d{12}', user_message.replace(' ', '').replace('-', ''))
        
        if aadhaar_match:
            aadhaar = aadhaar_match[0]
            
            # Verify Aadhaar using mock service
            aadhaar_result = verify_aadhaar(aadhaar)
            
            if not aadhaar_result['valid']:
                return {
                    'kyc_status': 'FAILED',
                    'flags': ['Invalid Aadhaar'],
                    'masked_data': {},
                    'reply': 'The Aadhaar number provided is invalid. Please check and provide a valid Aadhaar number.'
                }
            
            # Both verified
            return {
                'kyc_status': 'VERIFIED',
                'flags': [],
                'masked_data': {
                    'pan': loan_data.get('masked_pan', 'XXXXX1234X'),
                    'aadhaar': self.mask_aadhaar(aadhaar),
                    'pan_hash': loan_data.get('pan_hash', ''),
                    'aadhaar_hash': self.hash_identifier(aadhaar),
                    'aadhaar_name': aadhaar_result.get('name', 'Unknown'),
                    'aadhaar_address': aadhaar_result.get('address', 'Unknown')
                },
                'reply': f"""✅ Aadhaar verified successfully!
Name: {aadhaar_result.get('name', 'Unknown')}
Address: {aadhaar_result.get('address', 'Unknown')}"""
            }
        
        # No valid ID found
        return {
            'kyc_status': 'PENDING',
            'flags': [],
            'masked_data': {},
            'reply': 'Please provide your PAN number in the format: ABCDE1234F'
        }
