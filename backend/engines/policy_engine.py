"""
Policy Engine - Loads and validates loan applications against policy rules
"""

import json
import os
from typing import Dict, Any, List, Tuple
import logging

from config import POLICIES_DIR

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Policy engine for rule-based loan validation
    Loads JSON policy files and validates applications
    """
    
    def __init__(self):
        self.policies: Dict[str, Dict] = {}
        self.load_all_policies()
    
    def load_all_policies(self):
        """Load all policy files from policies directory"""
        try:
            for filename in os.listdir(POLICIES_DIR):
                if filename.endswith(".json"):
                    loan_type = filename.replace(".json", "")
                    policy_path = os.path.join(POLICIES_DIR, filename)
                    
                    with open(policy_path, 'r') as f:
                        policy = json.load(f)
                        self.policies[loan_type] = policy
                        logger.info(f"Loaded policy: {loan_type} (version {policy.get('version')})")
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            raise
    
    def get_policy(self, loan_type: str) -> Dict[str, Any]:
        """Get policy for a specific loan type"""
        policy = self.policies.get(loan_type)
        if not policy:
            raise ValueError(f"Policy not found for loan type: {loan_type}")
        return policy
    
    def validate_application(
        self,
        loan_type: str,
        application_data: Dict[str, Any],
        credit_score: int = None,
        bureau_data: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate loan application against policy rules
        Returns: (is_valid: bool, violations: List[str])
        """
        policy = self.get_policy(loan_type)
        violations = []
        
        # Eligibility rules validation
        eligibility = policy.get("eligibility_rules", {})
        
        # Age validation
        age = application_data.get("age")
        if age:
            if age < eligibility.get("min_age", 0):
                violations.append(f"Age {age} is below minimum required age {eligibility['min_age']}")
            if age > eligibility.get("max_age", 999):
                violations.append(f"Age {age} exceeds maximum allowed age {eligibility['max_age']}")
        
        # Credit score validation
        if credit_score is not None:
            min_score = eligibility.get("min_credit_score", 0)
            if credit_score < min_score:
                violations.append(f"Credit score {credit_score} is below minimum required {min_score}")
        
        # Income validation
        income = application_data.get("income")
        if income:
            min_income = eligibility.get("min_income", 0)
            if income < min_income:
                violations.append(f"Monthly income ₹{income} is below minimum required ₹{min_income}")
        
        # Employment type validation
        employment_type = application_data.get("employment_type")
        if employment_type:
            allowed_types = eligibility.get("employment_types_allowed", [])
            if employment_type not in allowed_types:
                violations.append(f"Employment type '{employment_type}' not allowed. Allowed: {allowed_types}")
        
        # Loan amount validation
        requested_amount = application_data.get("requested_amount")
        if requested_amount:
            loan_params = policy.get("loan_parameters", {})
            min_amount = loan_params.get("min_amount", 0)
            max_amount = loan_params.get("max_amount", float('inf'))
            
            if requested_amount < min_amount:
                violations.append(f"Requested amount ₹{requested_amount} is below minimum ₹{min_amount}")
            if requested_amount > max_amount:
                violations.append(f"Requested amount ₹{requested_amount} exceeds maximum ₹{max_amount}")
        
        # Tenure validation
        tenure_months = application_data.get("tenure_months")
        if tenure_months:
            loan_params = policy.get("loan_parameters", {})
            min_tenure = loan_params.get("min_tenure_months", 0)
            max_tenure = loan_params.get("max_tenure_months", 999)
            
            if tenure_months < min_tenure:
                violations.append(f"Tenure {tenure_months} months is below minimum {min_tenure} months")
            if tenure_months > max_tenure:
                violations.append(f"Tenure {tenure_months} months exceeds maximum {max_tenure} months")
        
        # Bureau criteria validation
        if bureau_data:
            bureau_criteria = policy.get("bureau_criteria", {})
            
            active_loans = bureau_data.get("active_loans", 0)
            max_active = bureau_criteria.get("max_active_loans", 999)
            if active_loans > max_active:
                violations.append(f"Active loans {active_loans} exceeds maximum allowed {max_active}")
            
            dpd_30 = bureau_data.get("dpd_30_days", 0)
            max_dpd = bureau_criteria.get("max_dpd_30_days", 999)
            if dpd_30 > max_dpd:
                violations.append(f"Days past due {dpd_30} exceeds maximum allowed {max_dpd}")
            
            bureau_flags = bureau_data.get("bureau_flags", [])
            if bureau_flags:
                violations.append(f"Bureau warning flags present: {', '.join(bureau_flags)}")
        
        is_valid = len(violations) == 0
        return is_valid, violations
    
    def get_interest_rate(
        self,
        loan_type: str,
        risk_segment: str,
        application_data: Dict[str, Any] = None
    ) -> float:
        """
        Get interest rate based on risk segment and policy
        Applies risk adjustments based on employment type, city tier, etc.
        """
        policy = self.get_policy(loan_type)
        interest_slabs = policy.get("interest_slabs", {})
        
        base_rate = interest_slabs.get(risk_segment, {}).get("rate", 15.0)
        
        # Apply adjustments
        if application_data:
            risk_adjustments = policy.get("risk_adjustments", {})
            adjustment = 0.0
            
# City tier adjustment
            city_tier = application_data.get("city_tier")
            if city_tier == 1:
                adjustment += risk_adjustments.get("city_tier_1_discount", 0)
            elif city_tier == 3:
                adjustment += risk_adjustments.get("city_tier_3_premium", 0)
            
            # Employment type adjustment
            if application_data.get("employment_type") == "self_employed":
                adjustment += risk_adjustments.get("self_employed_premium", 0)
            
            base_rate += adjustment
        
        return round(base_rate, 2)
    
    def calculate_max_eligible_amount(
        self,
        loan_type: str,
        income: float,
        existing_emi: float,
        tenure_months: int,
        interest_rate: float
    ) -> float:
        """
        Calculate maximum eligible loan amount based on FOIR
        """
        policy = self.get_policy(loan_type)
        foir_limit = policy.get("loan_parameters", {}).get("foir_limit", 0.5)
        
        # Maximum EMI based on FOIR
        max_emi = (income * foir_limit) - existing_emi
        
        if max_emi <= 0:
            return 0.0
        
        # Calculate principal using EMI formula: P = EMI * [(1 - (1 + r)^-n) / r]
        monthly_rate = interest_rate / (12 * 100)
        if monthly_rate == 0:
            principal = max_emi * tenure_months
        else:
            principal = max_emi * ((1 - (1 + monthly_rate) ** -tenure_months) / monthly_rate)
        
        # Cap at policy maximum
        max_amount = policy.get("loan_parameters", {}).get("max_amount", float('inf'))
        
        return min(round(principal, 2), max_amount)
    
    def get_processing_fee(self, loan_type: str, loan_amount: float) -> float:
        """Calculate processing fee based on policy"""
        policy = self.get_policy(loan_type)
        fees = policy.get("fees_and_charges", {})
        
        fee_percent = fees.get("processing_fee_percent", 2.0)
        fee_min = fees.get("processing_fee_min", 1000)
        fee_max = fees.get("processing_fee_max", 10000)
        
        fee = (loan_amount * fee_percent) / 100
        fee = max(fee, fee_min)
        fee = min(fee, fee_max)
        
        return round(fee, 2)
    
    def check_auto_approval_eligible(
        self,
        loan_type: str,
        application_data: Dict[str, Any],
        credit_score: int,
        foir: float
    ) -> bool:
        """Check if application is eligible for auto-approval"""
        policy = self.get_policy(loan_type)
        auto_approval = policy.get("auto_approval_criteria", {})
        
        if not auto_approval.get("enabled", False):
            return False
        
        # Check all auto-approval criteria
        if application_data.get("requested_amount", 0) > auto_approval.get("max_amount", 0):
            return False
        
        if credit_score < auto_approval.get("min_credit_score", 999):
            return False
        
        if foir > auto_approval.get("max_foir", 0):
            return False
        
        if application_data.get("employment_type") != auto_approval.get("employment_type"):
            return False
        
        return True


# Global instance
policy_engine = PolicyEngine()
