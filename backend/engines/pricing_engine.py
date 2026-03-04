"""
Pricing Engine - Interest rate determination and fee calculation
"""

import logging
from typing import Dict, Any

from engines.policy_engine import policy_engine

logger = logging.getLogger(__name__)


class PricingEngine:
    """
    Pricing engine for loan offers
    - Determines interest rate based on risk segment
    - Applies adjustments for employment type, city tier
    - Calculates fees and total cost
    """
    
    @staticmethod
    def determine_interest_rate(
        loan_type: str,
        risk_segment: str,
        application_data: Dict[str, Any]
    ) -> float:
        """
        Determine interest rate based on risk and applicant profile
        Uses policy engine for base rates and adjustments
        """
        try:
            # Get base rate from policy
            base_rate = policy_engine.get_interest_rate(
                loan_type, risk_segment, application_data
            )
            
            logger.info(
                f"Interest rate determined: {base_rate}% "
                f"(loan_type: {loan_type}, risk: {risk_segment})"
            )
            
            return base_rate
            
        except Exception as e:
            logger.error(f"Error determining interest rate: {e}")
            # Fallback rates
            fallback_rates = {"LOW": 12.0, "MEDIUM": 15.0, "HIGH": 18.0}
            return fallback_rates.get(risk_segment, 15.0)
    
    @staticmethod
    def calculate_total_interest(
        principal: float,
        monthly_emi: float,
        tenure_months: int
    ) -> float:
        """
        Calculate total interest payable over loan tenure
        Total Interest = (EMI × Tenure) - Principal
        """
        total_repayment = monthly_emi * tenure_months
        total_interest = total_repayment - principal
        
        return round(total_interest, 2)
    
    @staticmethod
    def calculate_processing_fee(
        loan_type: str,
        loan_amount: float
    ) -> Dict[str, float]:
        """
        Calculate processing fee and GST
        """
        try:
            fee = policy_engine.get_processing_fee(loan_type, loan_amount)
            gst = round(fee * 0.18, 2)  # 18% GST on processing fee
            total_fee = round(fee + gst, 2)
            
            return {
                "processing_fee": fee,
                "gst": gst,
                "total_processing_fee": total_fee
            }
            
        except Exception as e:
            logger.error(f"Error calculating processing fee: {e}")
            # Fallback: 2% with min 1000, max 10000
            fee = min(max(loan_amount * 0.02, 1000), 10000)
            gst = round(fee * 0.18, 2)
            return {
                "processing_fee": round(fee, 2),
                "gst": gst,
                "total_processing_fee": round(fee + gst, 2)
            }
    
    @staticmethod
    def generate_loan_offer(
        loan_type: str,
        risk_segment: str,
        eligible_amount: float,
        tenure_months: int,
        monthly_emi: float,
        application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive loan offer with all financial details
        """
        # Determine interest rate
        interest_rate = PricingEngine.determine_interest_rate(
            loan_type, risk_segment, application_data
        )
        
        # Calculate fees
        fees = PricingEngine.calculate_processing_fee(loan_type, eligible_amount)
        
        # Calculate total interest
        total_interest = PricingEngine.calculate_total_interest(
            eligible_amount, monthly_emi, tenure_months
        )
        
        # Total repayment
        total_repayment = monthly_emi * tenure_months
        
        # Net disbursement (after processing fee)
        net_disbursement = eligible_amount - fees["total_processing_fee"]
        
        # Effective Annual Percentage Rate (APR) - simplified
        # APR accounts for processing fees
        effective_apr = round(
            (total_interest + fees["total_processing_fee"]) / eligible_amount * (12 / tenure_months) * 100,
            2
        )
        
        return {
            "loan_type": loan_type,
            "principal": eligible_amount,
            "tenure_months": tenure_months,
            "interest_rate": interest_rate,
            "risk_segment": risk_segment,
            
            # EMI details
            "monthly_emi": monthly_emi,
            "total_emi_payments": tenure_months,
            
            # Financial breakdown
            "total_interest": total_interest,
            "total_repayment": total_repayment,
            "processing_fee": fees["processing_fee"],
            "processing_fee_gst": fees["gst"],
            "total_processing_fee": fees["total_processing_fee"],
            
            # Net amounts
            "gross_disbursement": eligible_amount,
            "net_disbursement": net_disbursement,
            
            # Effective rate
            "effective_apr": effective_apr,
            
            # Additional charges (from policy)
            "late_payment_charge": "2% per month on overdue amount",
            "prepayment_charge": "2% on principal outstanding (after 6 months)",
            "bounce_charge": 500,
            
            # Summary
            "summary": {
                "borrow": f"₹{eligible_amount:,.2f}",
                "receive": f"₹{net_disbursement:,.2f}",
                "pay_monthly": f"₹{monthly_emi:,.2f}",
                "total_payback": f"₹{total_repayment:,.2f}",
                "tenure": f"{tenure_months} months"
            }
        }


# Global instance
pricing_engine = PricingEngine()
