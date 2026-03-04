"""
LangChain Tools for Loan Workflow
Wraps deterministic engines as LangChain tools for LangGraph
"""

from typing import Dict, Any
from langchain.tools import tool
import logging

from engines.kyc_engine import kyc_engine
from engines.bureau_engine import bureau_engine
from engines.affordability_engine import affordability_engine
from engines.risk_engine import risk_engine
from engines.pricing_engine import pricing_engine
from engines.emi_engine import emi_engine
from engines.pdf_engine import pdf_engine
from engines.policy_engine import policy_engine

logger = logging.getLogger(__name__)


@tool
def verify_kyc(aadhaar: str, pan: str, user_id: str) -> Dict[str, Any]:
    """
    Verify KYC documents (Aadhaar and PAN)
    
    Args:
        aadhaar: 12-digit Aadhaar number
        pan: 10-character PAN number
        user_id: User ID for linking
    
    Returns:
        Dict with verification status, encrypted PII, masked values
    """
    try:
        result = kyc_engine.process_kyc(
            user_id=user_id,
            aadhaar=aadhaar,
            pan=pan
        )
        logger.info(f"KYC verification completed for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"KYC verification failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "aadhaar_verified": False,
            "pan_verified": False
        }


@tool
def fetch_credit_report(pan: str) -> Dict[str, Any]:
    """
    Fetch credit report from bureau
    
    Args:
        pan: PAN number
    
    Returns:
        Dict with credit score, active loans, outstanding amount, DPD, bureau flags
    """
    try:
        report = bureau_engine.fetch_credit_report(pan)
        analysis = bureau_engine.analyze_credit_report(report)
        
        result = {
            **report,
            "credit_tier": analysis["credit_tier"],
            "risk_category": analysis["risk_category"]
        }
        
        logger.info(f"Credit report fetched for PAN {pan}: Score {report.get('credit_score')}")
        return result
    except Exception as e:
        logger.error(f"Credit report fetch failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "credit_score": 0
        }


@tool
def validate_policy_eligibility(
    loan_type: str,
    age: int,
    credit_score: int,
    monthly_income: float,
    employment_type: str,
    requested_amount: float,
    tenure_months: int,
    existing_emi: float,
    active_loans: int,
    dpd_30_days: int
) -> Dict[str, Any]:
    """
    Validate loan application against policy rules
    
    Returns:
        Dict with is_eligible, violations list, max_eligible_amount
    """
    try:
        application_data = {
            "age": age,
            "credit_score": credit_score,
            "monthly_income": monthly_income,
            "employment_type": employment_type,
            "requested_amount": requested_amount,
            "tenure_months": tenure_months,
            "existing_emi": existing_emi
        }
        
        bureau_data = {
            "active_loans": active_loans,
            "dpd_30_days": dpd_30_days
        }
        
        is_eligible, violations = policy_engine.validate_application(
            loan_type, application_data, bureau_data
        )
        
        max_eligible = policy_engine.calculate_max_eligible_amount(
            loan_type, application_data
        )
        
        result = {
            "is_eligible": is_eligible,
            "violations": violations,
            "max_eligible_amount": max_eligible
        }
        
        logger.info(f"Policy validation: eligible={is_eligible}, violations={len(violations)}")
        return result
    except Exception as e:
        logger.error(f"Policy validation failed: {str(e)}")
        return {
            "is_eligible": False,
            "violations": [f"Validation error: {str(e)}"],
            "max_eligible_amount": 0
        }


@tool
def calculate_affordability(
    monthly_income: float,
    existing_emi: float,
    requested_amount: float,
    interest_rate: float,
    tenure_months: int,
    foir_limit: float = 0.60
) -> Dict[str, Any]:
    """
    Calculate loan affordability based on FOIR
    
    Returns:
        Dict with status, eligible_amount, max_emi_affordable, FOIR details
    """
    try:
        result = affordability_engine.determine_affordable_amount(
            monthly_income=monthly_income,
            existing_emi=existing_emi,
            requested_amount=requested_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            foir_limit=foir_limit
        )
        
        logger.info(f"Affordability calculated: {result['status']}, eligible={result['eligible_amount']}")
        return result
    except Exception as e:
        logger.error(f"Affordability calculation failed: {str(e)}")
        return {
            "status": "ERROR",
            "error": str(e),
            "eligible_amount": 0
        }


@tool
def assess_risk(
    credit_score: int,
    foir: float,
    employment_type: str,
    employment_years: int,
    city_tier: int,
    existing_emi: float,
    monthly_income: float,
    active_loans: int,
    dpd_30_days: int,
    bureau_flags: list
) -> Dict[str, Any]:
    """
    Perform comprehensive risk assessment
    
    Returns:
        Dict with risk_score (0-1), risk_segment, factors breakdown, recommendation
    """
    try:
        application_data = {
            "employment_type": employment_type,
            "employment_years": employment_years,
            "city_tier": city_tier,
            "existing_emi": existing_emi,
            "monthly_income": monthly_income
        }
        
        bureau_data = {
            "active_loans": active_loans,
            "dpd_30_days": dpd_30_days,
            "bureau_flags": bureau_flags
        }
        
        result = risk_engine.calculate_risk_score(
            credit_score, foir, application_data, bureau_data
        )
        
        # Add human-readable explanation
        result["explanation"] = risk_engine.explain_risk_factors(result)
        
        logger.info(f"Risk assessed: score={result['risk_score']:.2f}, segment={result['risk_segment']}")
        return result
    except Exception as e:
        logger.error(f"Risk assessment failed: {str(e)}")
        return {
            "risk_score": 1.0,
            "risk_segment": "HIGH",
            "recommendation": "REJECT",
            "error": str(e)
        }


@tool
def generate_loan_offer(
    loan_type: str,
    principal: float,
    tenure_months: int,
    risk_segment: str,
    age: int,
    employment_type: str,
    city_tier: int
) -> Dict[str, Any]:
    """
    Generate comprehensive loan offer with all financial details
    
    Returns:
        Dict with interest rate, EMI, fees, total repayment, net disbursement
    """
    try:
        application_data = {
            "age": age,
            "employment_type": employment_type,
            "city_tier": city_tier
        }
        
        offer = pricing_engine.generate_loan_offer(
            loan_type=loan_type,
            loan_amount=principal,
            tenure_months=tenure_months,
            risk_segment=risk_segment,
            application_data=application_data
        )
        
        logger.info(f"Loan offer generated: ₹{principal} @ {offer['interest_rate']}%, EMI ₹{offer['monthly_emi']}")
        return offer
    except Exception as e:
        logger.error(f"Offer generation failed: {str(e)}")
        return {
            "error": str(e),
            "principal": 0,
            "monthly_emi": 0
        }


@tool
def generate_emi_schedule(
    principal: float,
    interest_rate: float,
    tenure_months: int,
    disbursement_date: str
) -> Dict[str, Any]:
    """
    Generate month-by-month amortization schedule
    
    Returns:
        Dict with schedule array and summary
    """
    try:
        schedule = emi_engine.generate_amortization_schedule(
            principal=principal,
            annual_interest_rate=interest_rate,
            tenure_months=tenure_months,
            disbursement_date=disbursement_date
        )
        
        summary = emi_engine.get_schedule_summary(schedule)
        
        result = {
            "schedule": schedule,
            "summary": summary
        }
        
        logger.info(f"EMI schedule generated: {len(schedule)} installments")
        return result
    except Exception as e:
        logger.error(f"EMI schedule generation failed: {str(e)}")
        return {
            "error": str(e),
            "schedule": [],
            "summary": {}
        }


@tool
def generate_sanction_letter(
    loan_id: str,
    application_data: Dict[str, Any],
    offer_data: Dict[str, Any],
    user_data: Dict[str, Any],
    emi_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate PDF sanction letter
    
    Returns:
        Dict with file_path and download_url
    """
    try:
        filepath = pdf_engine.generate_sanction_letter(
            loan_id=loan_id,
            application_data=application_data,
            offer_data=offer_data,
            user_data=user_data,
            emi_schedule_summary=emi_summary
        )
        
        result = {
            "success": True,
            "file_path": filepath,
            "download_url": f"/api/loans/{loan_id}/sanction-letter"
        }
        
        logger.info(f"Sanction letter generated: {filepath}")
        return result
    except Exception as e:
        logger.error(f"Sanction letter generation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# Export all tools
ALL_TOOLS = [
    verify_kyc,
    fetch_credit_report,
    validate_policy_eligibility,
    calculate_affordability,
    assess_risk,
    generate_loan_offer,
    generate_emi_schedule,
    generate_sanction_letter
]
