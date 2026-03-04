"""
EMI Engine - Amortization schedule generation
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class EMIEngine:
    """
    EMI and amortization schedule engine
    - Generates complete EMI schedule
    - Calculates principal/interest breakdown for each installment
    - Tracks remaining balance
    """
    
    @staticmethod
    def calculate_emi(
        principal: float,
        annual_interest_rate: float,
        tenure_months: int
    ) -> float:
        """
        Calculate monthly EMI
        EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
        """
        if annual_interest_rate == 0:
            return round(principal / tenure_months, 2)
        
        monthly_rate = annual_interest_rate / (12 * 100)
        
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / (
            (1 + monthly_rate) ** tenure_months - 1
        )
        
        return round(emi, 2)
    
    @staticmethod
    def generate_amortization_schedule(
        principal: float,
        annual_interest_rate: float,
        tenure_months: int,
        disbursement_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Generate complete amortization schedule
        Returns list of installments with principal/interest breakdown
        """
        if disbursement_date is None:
            disbursement_date = datetime.utcnow()
        
        # Calculate EMI
        emi = EMIEngine.calculate_emi(principal, annual_interest_rate, tenure_months)
        
        monthly_rate = annual_interest_rate / (12 * 100)
        remaining_balance = principal
        schedule = []
        
        for month in range(1, tenure_months + 1):
            # Calculate interest for this month
            interest_component = round(remaining_balance * monthly_rate, 2)
            
            # Principal component
            principal_component = round(emi - interest_component, 2)
            
            # Handle last installment rounding
            if month == tenure_months:
                principal_component = remaining_balance
                emi = principal_component + interest_component
            
            # Update remaining balance
            remaining_balance -= principal_component
            remaining_balance = max(0, round(remaining_balance, 2))  # Avoid negative due to rounding
            
            # Calculate due date (first day of month, starting from next month)
            due_date = disbursement_date + relativedelta(months=month)
            due_date = due_date.replace(day=1)  # Set to 1st of month
            
            installment = {
                "month": month,
                "due_date": due_date,
                "emi_amount": emi,
                "principal_component": principal_component,
                "interest_component": interest_component,
                "remaining_balance": remaining_balance,
                "status": "PENDING",
                "paid_date": None,
                "payment_transaction_id": None
            }
            
            schedule.append(installment)
        
        logger.info(f"Generated amortization schedule: {tenure_months} installments, EMI: ₹{emi}")
        
        return schedule
    
    @staticmethod
    def get_schedule_summary(schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics from amortization schedule
        """
        if not schedule:
            return {}
        
        total_principal = sum(inst["principal_component"] for inst in schedule)
        total_interest = sum(inst["interest_component"] for inst in schedule)
        total_payment = sum(inst["emi_amount"] for inst in schedule)
        
        return {
            "total_installments": len(schedule),
            "total_principal": round(total_principal, 2),
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_payment, 2),
            "first_due_date": schedule[0]["due_date"],
            "last_due_date": schedule[-1]["due_date"],
            "monthly_emi": schedule[0]["emi_amount"]
        }
    
    @staticmethod
    def calculate_prepayment_details(
        schedule: List[Dict[str, Any]],
        current_month: int,
        prepayment_amount: float,
        prepayment_charge_percent: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculate prepayment impact and charges
        """
        if current_month < 1 or current_month > len(schedule):
            return {"error": "Invalid month"}
        
        # Get current outstanding
        outstanding_principal = schedule[current_month - 1]["remaining_balance"]
        
        if prepayment_amount > outstanding_principal:
            prepayment_amount = outstanding_principal
        
        # Calculate prepayment charge
        prepayment_charge = round((prepayment_amount * prepayment_charge_percent) / 100, 2)
        
        # New outstanding after prepayment
        new_outstanding = outstanding_principal - prepayment_amount
        
        # Interest savings (rough estimate)
        remaining_months = len(schedule) - current_month
        avg_monthly_interest = schedule[current_month]["interest_component"]
        estimated_interest_savings = round(
            avg_monthly_interest * remaining_months * (prepayment_amount / outstanding_principal),
            2
        )
        
        return {
            "current_outstanding": outstanding_principal,
            "prepayment_amount": prepayment_amount,
            "prepayment_charge": prepayment_charge,
            "total_payment_required": prepayment_amount + prepayment_charge,
            "new_outstanding": new_outstanding,
            "estimated_interest_savings": estimated_interest_savings,
            "net_benefit": estimated_interest_savings - prepayment_charge
        }


# Global instance
emi_engine = EMIEngine()
