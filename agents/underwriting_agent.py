"""
Credit & Underwriting Agent

Inputs:
- loan request
- KYC result
- mock CIBIL score
- mock income data

Logic:
- Dynamic FOIR
- Explainable risk decision
- Tier-based approval
"""

import random
from typing import Dict, Any
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_services.cibil_api import get_cibil_score

class UnderwritingAgent:
    def __init__(self):
        self.min_cibil = 650
        self.max_foir = 50  # Maximum 50% FOIR
    
    def calculate_foir(self, monthly_income: float, emi: float) -> float:
        """Calculate Fixed Obligation to Income Ratio"""
        if monthly_income <= 0:
            return 100.0
        return round((emi / monthly_income) * 100, 2)
    
    def calculate_emi(self, loan_amount: float, tenure: int, interest_rate: float = 12.5) -> float:
        """Calculate monthly EMI"""
        monthly_rate = interest_rate / 12 / 100
        emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
        return round(emi, 2)
    
    def assess_risk(self, credit_score: int, foir: float, loan_amount: float) -> str:
        """Determine risk level"""
        if credit_score < 650:
            return 'HIGH'
        elif credit_score < 700:
            if foir > 45 or loan_amount > 500000:
                return 'HIGH'
            return 'MEDIUM'
        elif credit_score < 750:
            if foir > 50:
                return 'MEDIUM'
            return 'LOW'
        else:
            if foir > 50:
                return 'MEDIUM'
            return 'LOW'
    
    def process(self, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform credit assessment
        Returns approval decision with reasoning
        """
        
        # Get loan details
        loan_amount = loan_data.get('loan_amount', 0)
        tenure = loan_data.get('tenure', 12)
        pan_hash = loan_data.get('pan_hash', 'unknown')
        
        # Get CIBIL score from mock service
        cibil_data = get_cibil_score(pan_hash)
        credit_score = cibil_data['score']
        
        # Mock monthly income (in production, get from salary slips)
        # For demo, calculate based on loan amount
        estimated_monthly_income = max(loan_amount / 10, 30000)  # At least 30k
        
        # Add some randomness
        monthly_income = round(estimated_monthly_income + random.randint(-10000, 10000), 2)
        
        # Calculate EMI
        interest_rate = 12.5
        emi = self.calculate_emi(loan_amount, tenure, interest_rate)
        
        # Calculate FOIR
        foir = self.calculate_foir(monthly_income, emi)
        
        # Assess risk
        risk_level = self.assess_risk(credit_score, foir, loan_amount)
        
        # Determine approved amount
        if risk_level == 'HIGH':
            approved_amount = int(loan_amount * 0.5)  # Reduce by 50%
            reasoning = f"""Risk Assessment: HIGH

Factors:
- Credit Score: {credit_score} (Below optimal range)
- FOIR: {foir}% (High debt burden)
- Approved Amount reduced to ₹{approved_amount:,} (50% of requested)

Recommendation: Improve credit score or reduce loan amount."""
        
        elif risk_level == 'MEDIUM':
            approved_amount = int(loan_amount * 0.85)  # Reduce by 15%
            reasoning = f"""Risk Assessment: MEDIUM

Factors:
- Credit Score: {credit_score} (Fair range)
- FOIR: {foir}% (Acceptable)
- Approved Amount: ₹{approved_amount:,} (85% of requested)

Recommendation: Consider slightly lower loan amount for better terms."""
        
        else:  # LOW
            approved_amount = loan_amount
            reasoning = f"""Risk Assessment: LOW

Factors:
- Credit Score: {credit_score} (Excellent range)
- FOIR: {foir}% (Comfortable)
- Approved Amount: ₹{approved_amount:,} (100% approved!)

Congratulations! You qualify for the full loan amount."""
        
        return {
            'credit_score': credit_score,
            'foir': foir,
            'risk_level': risk_level,
            'approved_amount': approved_amount,
            'monthly_income': monthly_income,
            'emi': emi,
            'interest_rate': interest_rate,
            'reasoning': reasoning
        }
