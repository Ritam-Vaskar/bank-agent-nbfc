"""Mock CIBIL API - Credit Score Service"""

import random
from typing import Dict, Any

def get_cibil_score(pan: str) -> Dict[str, Any]:
    """
    Get mock CIBIL score for PAN
    In production, this would call actual CIBIL API
    """
    
    # Generate deterministic score based on PAN hash
    # This ensures same PAN always gets same score
    hash_value = sum(ord(c) for c in pan)
    random.seed(hash_value)
    
    # Generate score in realistic range
    score = random.randint(650, 850)
    
    # Determine credit history
    if score >= 750:
        history = "Excellent"
        defaults = 0
    elif score >= 700:
        history = "Good"
        defaults = random.randint(0, 1)
    elif score >= 650:
        history = "Fair"
        defaults = random.randint(1, 2)
    else:
        history = "Poor"
        defaults = random.randint(2, 5)
    
    return {
        'score': score,
        'history': history,
        'total_accounts': random.randint(2, 8),
        'active_loans': random.randint(0, 3),
        'defaults': defaults,
        'credit_utilization': random.randint(20, 70),
        'oldest_account_years': random.randint(1, 15)
    }

def get_credit_report(pan: str) -> Dict[str, Any]:
    """
    Get detailed credit report
    """
    score_data = get_cibil_score(pan)
    
    return {
        **score_data,
        'report_date': '2024-01-27',
        'enquiries_last_6_months': random.randint(0, 5),
        'payment_history': 'Mostly on-time' if score_data['score'] > 700 else 'Some delays',
        'recommendation': 'Approved' if score_data['score'] >= 700 else 'Review required'
    }
