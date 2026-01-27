"""Mock PAN Verification API"""

import random
import re
from typing import Dict, Any

# Mock database of valid PAN numbers
MOCK_PAN_DB = {
    'ABCDE1234F': {
        'name': 'Rajesh Kumar',
        'type': 'Individual',
        'status': 'Active'
    },
    'PQRST5678G': {
        'name': 'Priya Sharma',
        'type': 'Individual',
        'status': 'Active'
    },
    'XYZAB9012H': {
        'name': 'Amit Patel',
        'type': 'Individual',
        'status': 'Active'
    }
}

def verify_pan(pan: str) -> Dict[str, Any]:
    """
    Verify PAN number
    Returns validation status and details
    """
    
    # Check format: 5 letters, 4 digits, 1 letter
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    
    if not re.match(pan_pattern, pan.upper()):
        return {
            'valid': False,
            'message': 'Invalid PAN format. Expected format: ABCDE1234F'
        }
    
    pan = pan.upper()
    
    # Check if in mock database
    if pan in MOCK_PAN_DB:
        data = MOCK_PAN_DB[pan]
        return {
            'valid': True,
            'verified': True,
            **data
        }
    
    # Generate mock data for any other valid format
    # For demo purposes, accept any valid format
    first_names = ['Rajesh', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali', 'Ravi', 'Deepa']
    last_names = ['Kumar', 'Sharma', 'Patel', 'Singh', 'Reddy', 'Nair', 'Gupta', 'Verma']
    
    # Generate deterministic name based on PAN
    hash_value = sum(ord(c) for c in pan)
    random.seed(hash_value)
    
    # PAN 4th character indicates type
    pan_type_char = pan[3]
    if pan_type_char == 'P':
        pan_type = 'Individual'
    elif pan_type_char == 'C':
        pan_type = 'Company'
    elif pan_type_char == 'F':
        pan_type = 'Firm'
    else:
        pan_type = 'Individual'
    
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    
    return {
        'valid': True,
        'verified': True,
        'name': name,
        'type': pan_type,
        'status': 'Active'
    }

def link_aadhaar_pan(pan: str, aadhaar: str) -> Dict[str, Any]:
    """
    Check if Aadhaar is linked to PAN
    """
    # For demo, assume all valid PANs and Aadhaars are linked
    return {
        'linked': True,
        'message': 'Aadhaar is linked to PAN'
    }

def get_pan_details(pan: str) -> Dict[str, Any]:
    """
    Get detailed PAN information
    """
    basic_info = verify_pan(pan)
    
    if not basic_info['valid']:
        return basic_info
    
    return {
        **basic_info,
        'registration_date': f"{random.randint(2000, 2020)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        'jurisdiction': random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']),
        'last_updated': '2024-01-15'
    }
