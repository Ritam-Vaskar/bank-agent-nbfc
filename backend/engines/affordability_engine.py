"""
Affordability Engine - FOIR calculation and eligible amount determination
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AffordabilityEngine:
    """
    Affordability calculation engine
    - Calculates Fixed Obligations to Income Ratio (FOIR)
    - Determines maximum eligible EMI
    - Back-calculates maximum principal amount
    """
    
    @staticmethod
    def calculate_foir(
        gross_monthly_income: float,
        existing_emi: float,
        proposed_emi: float
    ) -> float:
        """
        Calculate FOIR (Fixed Obligations to Income Ratio)
        FOIR = (Existing EMI + Proposed EMI) / Gross Monthly Income
        """
        if gross_monthly_income <= 0:
            return 1.0  # Invalid income, 100% FOIR
        
        total_obligations = existing_emi + proposed_emi
        foir = total_obligations / gross_monthly_income
        
        return round(foir, 4)
    
    @staticmethod
    def calculate_max_emi(
        gross_monthly_income: float,
        existing_emi: float,
        foir_limit: float = 0.6
    ) -> float:
        """
        Calculate maximum EMI affordability based on FOIR limit
        Max EMI = (Income × FOIR Limit) - Existing EMI
        """
        if gross_monthly_income <= 0:
            return 0.0
        
        max_total_obligations = gross_monthly_income * foir_limit
        max_emi = max_total_obligations - existing_emi
        
        return max(0, round(max_emi, 2))
    
    @staticmethod
    def calculate_emi(
        principal: float,
        annual_interest_rate: float,
        tenure_months: int
    ) -> float:
        """
        Calculate EMI using standard formula
        EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
        where:
            P = principal
            r = monthly interest rate (annual/12/100)
            n = tenure in months
        """
        if principal <= 0 or tenure_months <= 0:
            return 0.0
        
        if annual_interest_rate == 0:
            # Interest-free loan
            return round(principal / tenure_months, 2)
        
        monthly_rate = annual_interest_rate / (12 * 100)
        
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / (
            (1 + monthly_rate) ** tenure_months - 1
        )
        
        return round(emi, 2)
    
    @staticmethod
    def calculate_max_principal(
        max_emi: float,
        annual_interest_rate: float,
        tenure_months: int
    ) -> float:
        """
        Back-calculate maximum principal from EMI
        P = EMI × [(1 - (1 + r)^-n) / r]
        """
        if max_emi <= 0 or tenure_months <= 0:
            return 0.0
        
        if annual_interest_rate == 0:
            # Interest-free
            return round(max_emi * tenure_months, 2)
        
        monthly_rate = annual_interest_rate / (12 * 100)
        
        principal = max_emi * ((1 - (1 + monthly_rate) ** -tenure_months) / monthly_rate)
        
        return round(principal, 2)
    
    @staticmethod
    def determine_affordable_amount(
        income: float,
        existing_emi: float,
        requested_amount: float,
        tenure_months: int,
        interest_rate: float,
        foir_limit: float = 0.6,
        policy_max_amount: float = None
    ) -> Dict[str, Any]:
        """
        Comprehensive affordability assessment
        Returns eligible amount and analysis
        """
        # Calculate maximum EMI based on FOIR
        max_emi = AffordabilityEngine.calculate_max_emi(income, existing_emi, foir_limit)
        
        # Calculate maximum principal affordable
        max_principal_foir = AffordabilityEngine.calculate_max_principal(
            max_emi, interest_rate, tenure_months
        )
        
        # Apply policy maximum if exists
        if policy_max_amount:
            max_principal_policy = min(max_principal_foir, policy_max_amount)
        else:
            max_principal_policy = max_principal_foir
        
        # Calculate EMI for requested amount
        requested_emi = AffordabilityEngine.calculate_emi(
            requested_amount, interest_rate, tenure_months
        )
        
        # Calculate FOIR for requested amount
        foir_requested = AffordabilityEngine.calculate_foir(
            income, existing_emi, requested_emi
        )
        
        # Determine eligible amount
        if requested_amount <= max_principal_policy:
            eligible_amount = requested_amount
            status = "APPROVED"
            message = "Requested amount is within affordability"
        else:
            eligible_amount = max_principal_policy
            status = "REDUCED"
            message = f"Requested amount exceeds affordability. Maximum eligible: ₹{eligible_amount:,.2f}"
        
        # Check if any amount is affordable
        if eligible_amount <= 0:
            status = "REJECTED"
            message = "Income insufficient for any loan amount given existing obligations"
            eligible_amount = 0
        
        return {
            "status": status,
            "eligible_amount": eligible_amount,
            "requested_amount": requested_amount,
            "max_emi_affordable": max_emi,
            "requested_emi": requested_emi,
            "eligible_emi": AffordabilityEngine.calculate_emi(
                eligible_amount, interest_rate, tenure_months
            ),
            "foir_requested": foir_requested,
            "foir_limit": foir_limit,
            "foir_eligible": AffordabilityEngine.calculate_foir(
                income,
                existing_emi,
                AffordabilityEngine.calculate_emi(eligible_amount, interest_rate, tenure_months)
            ),
            "message": message,
            "income": income,
            "existing_emi": existing_emi
        }


# Global instance
affordability_engine = AffordabilityEngine()
