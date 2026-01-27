"""Mock Aadhaar Verification API"""

import random
from typing import Dict, Any

# Mock database of valid Aadhaar numbers
MOCK_AADHAAR_DB = {
    '123456789012': {
        'name': 'Rajesh Kumar',
        'dob': '1990-05-15',
        'gender': 'Male',
        'address': 'House No 123, MG Road, Bangalore, Karnataka - 560001'
    },
    '234567890123': {
        'name': 'Priya Sharma',
        'dob': '1992-08-20',
        'gender': 'Female',
        'address': 'Flat 456, Sector 12, Noida, Uttar Pradesh - 201301'
    },
    '345678901234': {
        'name': 'Amit Patel',
        'dob': '1988-12-10',
        'gender': 'Male',
        'address': 'Plot No 789, Navrangpura, Ahmedabad, Gujarat - 380009'
    }
}

def verify_aadhaar(aadhaar: str) -> Dict[str, Any]:
    """
    Verify Aadhaar number
    Returns validation status and details
    """
    
    # Check format
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        return {
            'valid': False,
            'message': 'Invalid Aadhaar format'
        }
    
    # Check if in mock database
    if aadhaar in MOCK_AADHAAR_DB:
        data = MOCK_AADHAAR_DB[aadhaar]
        return {
            'valid': True,
            'verified': True,
            **data
        }
    
    # Generate mock data for any other 12-digit number
    # For demo purposes, accept any valid format
    first_names = ['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali', 'Ravi', 'Deepa']
    last_names = ['Kumar', 'Sharma', 'Patel', 'Singh', 'Reddy', 'Nair', 'Gupta', 'Verma']
    cities = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad']
    states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'West Bengal', 'Telangana', 'Gujarat']
    
    # Generate deterministic data based on Aadhaar number
    hash_value = int(aadhaar[:4])
    random.seed(hash_value)
    
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    city = random.choice(cities)
    state = random.choice(states)
    pincode = random.randint(400001, 600001)
    
    return {
        'valid': True,
        'verified': True,
        'name': name,
        'dob': f"{random.randint(1980, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        'gender': random.choice(['Male', 'Female']),
        'address': f"House No {random.randint(1, 999)}, {city}, {state} - {pincode}"
    }

def send_otp(aadhaar: str, mobile: str) -> Dict[str, Any]:
    """
    Send OTP to mobile for Aadhaar verification
    """
    otp = random.randint(100000, 999999)
    
    return {
        'success': True,
        'otp': otp,  # In production, don't return OTP, send via SMS
        'message': f'OTP sent to mobile number ending with {mobile[-4:]}'
    }

def verify_otp(aadhaar: str, otp: str) -> Dict[str, Any]:
    """
    Verify OTP
    """
    # For demo, accept any 6-digit OTP
    if len(str(otp)) == 6:
        return {
            'success': True,
            'verified': True
        }
    
    return {
        'success': False,
        'verified': False,
        'message': 'Invalid OTP'
    }
