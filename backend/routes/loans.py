"""
Loan Application Routes
Integrates LangGraph workflow with HTTP endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Any
from datetime import datetime
import logging
import uuid

from auth.dependencies import get_current_user
from models.user import User
from models.loan_application import LoanApplication, ApplicationData, ConversationMessage, ChatMessage
from models.loan import Loan
from database import mongodb, redis_client
from workflows.loan_graph import (
    LoanWorkflowState,
    REQUIRED_APPLICATION_FIELDS,
    generate_follow_up_response,
    handle_acceptance_node,
    run_workflow_stepwise,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loans", tags=["Loans"])

ACCEPTANCE_KEYWORDS = ("accept", "yes", "agree", "confirm")
REJECTION_KEYWORDS = ("reject", "no", "decline", "cancel")
AUTOFILL_KEYWORDS = ("auto", "autofill", "demo", "autofill demo")
CONTINUE_KEYWORDS = ("ok", "okay", "continue", "next", "start", "initiate", "do")
STEP_CONFIRMATION_STAGES = {
    "verify_kyc",
    "fetch_credit",
    "check_policy",
    "assess_affordability",
    "assess_risk",
    "generate_offer",
    "generate_sanction",
    "simulate_disbursement",
}


def _build_pipeline_progress(state: LoanWorkflowState, status_value: str | None = None) -> Dict[str, Any]:
    kyc_data = state.get("kyc_data") or {}
    credit_data = state.get("credit_data") or {}

    return {
        "kyc_done": kyc_data.get("kyc_status") == "VERIFIED",
        "credit_done": credit_data.get("credit_score") is not None,
        "policy_done": state.get("policy_validation") is not None,
        "affordability_done": state.get("affordability_result") is not None,
        "risk_done": state.get("risk_assessment") is not None,
        "offer_done": state.get("loan_offer") is not None,
        "sanction_done": state.get("sanction_letter_path") is not None,
        "current_stage": state.get("stage"),
        "status": status_value,
    }


def _normalize_loan_type(loan_type: str) -> str:
    if loan_type.endswith("_loan"):
        return loan_type
    return f"{loan_type}_loan"


@router.post("/apply")
async def start_loan_application(
    loan_type: str | None = None,
    payload: Dict[str, Any] | None = Body(default=None),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize a new loan application workflow
    
    Args:
        loan_type: Type of loan (personal_loan, home_loan, etc.)
        current_user: Authenticated user
    
    Returns:
        Application ID and initial state
    """
    try:
        if not loan_type and payload:
            loan_type = payload.get("loan_type")

        if not loan_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="loan_type is required"
            )

        loan_type = _normalize_loan_type(loan_type)
        application_id = str(uuid.uuid4())
        
        # Initialize workflow state
        initial_state: LoanWorkflowState = {
            "application_id": application_id,
            "user_id": current_user.user_id,
            "loan_type": loan_type,
            "stage": "init",
            "application_data": {},
            "kyc_data": None,
            "credit_data": None,
            "policy_validation": None,
            "affordability_result": None,
            "risk_assessment": None,
            "loan_offer": None,
            "emi_schedule": None,
            "loan_id": None,
            "sanction_letter_path": None,
            "messages": [],
            "is_eligible": True,
            "is_accepted": False,
            "rejection_reason": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Run first two nodes (init + collect_info greeting)
        # Use recursion_limit to prevent infinite loops
        result_state = run_workflow_stepwise(initial_state)
        
        # Save application to database
        application_doc = {
            "application_id": application_id,
            "user_id": current_user.user_id,
            "loan_type": loan_type,
            "status": "IN_PROGRESS",
            "workflow_stage": result_state["stage"],
            "application_data": result_state["application_data"],
            "conversation_messages": result_state["messages"],
            "progress": _build_pipeline_progress(result_state, "IN_PROGRESS"),
            "is_eligible": result_state["is_eligible"],
            "is_accepted": result_state["is_accepted"],
            "created_at": result_state["created_at"],
            "updated_at": result_state["updated_at"]
        }
        
        await mongodb.loan_applications.insert_one(application_doc)
        
        logger.info(f"Loan application {application_id} created for user {current_user.user_id}")
        
        return {
            "application_id": application_id,
            "loan_type": loan_type,
            "status": "IN_PROGRESS",
            "stage": result_state["stage"],
            "messages": result_state["messages"],
            "progress": _build_pipeline_progress(result_state, "IN_PROGRESS")
        }
        
    except Exception as e:
        logger.error(f"Error starting loan application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start application: {str(e)}"
        )


@router.post("/applications/{application_id}/chat")
async def chat_with_workflow(
    application_id: str,
    chat_message: ChatMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the loan workflow and get response
    This is the main interaction endpoint for the conversational interface
    
    Args:
        application_id: Application ID
        chat_message: User's message and metadata
        current_user: Authenticated user
    
    Returns:
        Updated conversation and workflow state
    """
    try:
        message = chat_message.message
        
        # Fetch current application state
        app_doc = await mongodb.loan_applications.find_one({
            "application_id": application_id,
            "user_id": current_user.user_id
        })
        
        if not app_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Reconstruct workflow state
        state: LoanWorkflowState = {
            "application_id": application_id,
            "user_id": current_user.user_id,
            "loan_type": app_doc["loan_type"],
            "stage": app_doc["workflow_stage"],
            "application_data": app_doc.get("application_data", {}),
            "kyc_data": app_doc.get("kyc_data"),
            "credit_data": app_doc.get("credit_data"),
            "policy_validation": app_doc.get("policy_validation"),
            "affordability_result": app_doc.get("affordability_result"),
            "risk_assessment": app_doc.get("risk_assessment"),
            "loan_offer": app_doc.get("loan_offer"),
            "emi_schedule": app_doc.get("emi_schedule"),
            "loan_id": app_doc.get("loan_id"),
            "sanction_letter_path": app_doc.get("sanction_letter_path"),
            "messages": app_doc["conversation_messages"],
            "is_eligible": app_doc["is_eligible"],
            "is_accepted": app_doc["is_accepted"],
            "rejection_reason": app_doc.get("rejection_reason"),
            "created_at": app_doc["created_at"],
            "updated_at": datetime.now().isoformat()
        }
        
        # Add user message to state
        state["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        message_lower = message.lower()
        is_acceptance_message = any(word in message_lower for word in ACCEPTANCE_KEYWORDS)
        is_rejection_message = any(word in message_lower for word in REJECTION_KEYWORDS)
        is_continue_message = any(word in message_lower for word in CONTINUE_KEYWORDS)
        
        # Parse application data if in collection stage
        if state["stage"] == "collect_info":
            # Extract data from message (simple keyword matching)
            # In production, use better NLP or structured forms
            app_data = state["application_data"]

            if any(word == message_lower.strip() for word in AUTOFILL_KEYWORDS):
                app_data.setdefault("aadhaar", "123456789012")
                app_data.setdefault("pan", "ABCDE1234F")
                app_data.setdefault("monthly_income", 75000.0)
                app_data.setdefault("requested_amount", 300000.0)
                app_data.setdefault("tenure_months", 24)
                app_data.setdefault("age", 30)
                app_data.setdefault("employment_type", "salaried")
                app_data.setdefault("employment_years", 5)
                app_data.setdefault("city_tier", 1)
                state["messages"].append({
                    "role": "assistant",
                    "content": (
                        "Auto-filled sample KYC and financial details for demo flow. "
                        "Proceeding with mock UIDAI and bureau checks now."
                    ),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Extract Aadhaar
            import re
            aadhaar_match = re.search(r'\b\d{12}\b', message)
            if aadhaar_match:
                app_data["aadhaar"] = aadhaar_match.group()
            
            # Extract PAN
            pan_match = re.search(r'\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b', message)
            if pan_match:
                app_data["pan"] = pan_match.group().upper()
            
            # Extract income (look for numbers with "income" or "salary")
            if any(word in message_lower for word in ["income", "salary", "earn"]):
                income_match = re.search(r'\b(\d{4,7})\b', message)
                if income_match:
                    app_data["monthly_income"] = float(income_match.group())
            
            # Extract amount (look for numbers with "amount" or "need")
            if any(word in message_lower for word in ["amount", "need", "loan", "borrow"]):
                amount_match = re.search(r'\b(\d{5,8})\b', message)
                if amount_match:
                    app_data["requested_amount"] = float(amount_match.group())

            # Extract amount in lakh notation (e.g., 1 lakh, 2.5 lakh, 1lakh)
            lakh_match = re.search(r'\b(\d+(?:\.\d+)?)\s*lakh\b', message_lower)
            if lakh_match and not app_data.get("requested_amount"):
                app_data["requested_amount"] = float(lakh_match.group(1)) * 100000
            
            # Extract tenure
            tenure_context = (
                any(word in message_lower for word in ["month", "months", "moth", "moths", "tenure", "period", "mth", "mo"]) or
                ("year" in message_lower and any(word in message_lower for word in ["loan", "repay", "duration", "term"]))
            )
            if tenure_context:
                tenure_match = re.search(r'\b(\d{1,3})\b', message)
                if tenure_match:
                    tenure = int(tenure_match.group())
                    # Convert years to months if needed
                    if "year" in message_lower and tenure <= 10:
                        tenure *= 12
                    app_data["tenure_months"] = tenure
            
            # Extract age
            if "age" in message_lower or "old" in message_lower:
                age_match = re.search(r'\b(\d{2})\b', message)
                if age_match:
                    app_data["age"] = int(age_match.group())

            # Fallback for standalone numeric messages (common chat pattern)
            numeric_match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*', message)
            if numeric_match:
                numeric_value = float(numeric_match.group(1))

                if not app_data.get("monthly_income") and 5000 <= numeric_value <= 1000000:
                    app_data["monthly_income"] = numeric_value
                elif (
                    not app_data.get("age")
                    and 18 <= numeric_value <= 80
                    and (
                        app_data.get("employment_years")
                        or app_data.get("employment_type")
                        or app_data.get("tenure_months")
                    )
                ):
                    app_data["age"] = int(numeric_value)
                elif not app_data.get("tenure_months") and 6 <= numeric_value <= 360:
                    app_data["tenure_months"] = int(numeric_value)
                elif not app_data.get("age") and 18 <= numeric_value <= 80:
                    app_data["age"] = int(numeric_value)
                elif not app_data.get("requested_amount") and 10000 <= numeric_value <= 50000000:
                    app_data["requested_amount"] = numeric_value
            
            # Extract employment type
            if "salaried" in message_lower or "employee" in message_lower:
                app_data["employment_type"] = "salaried"
            elif "self" in message_lower or "business" in message_lower:
                app_data["employment_type"] = "self_employed"
            
            # Extract employment years
            if any(word in message_lower for word in ["experience", "working", "employed"]):
                exp_match = re.search(r'\b(\d{1,2})\b', message)
                if exp_match:
                    app_data["employment_years"] = int(exp_match.group())

            # Extract employment years from compact formats (e.g., 10yrs, 7 yr, 5years)
            exp_compact_match = re.search(r'\b(\d{1,2})\s*(?:yrs?|years?)\b', message_lower)
            if exp_compact_match:
                app_data["employment_years"] = int(exp_compact_match.group(1))
            
            # Extract city tier
            if "tier" in message_lower:
                tier_match = re.search(r'tier\s*[- ]?\s*([123])\b', message_lower)
                if not tier_match:
                    tier_match = re.search(r'\b([123])\b', message)
                if tier_match:
                    app_data["city_tier"] = int(tier_match.group(1))
            elif any(city in message_lower for city in ["mumbai", "delhi", "bangalore", "chennai", "kolkata", "hyderabad"]):
                app_data["city_tier"] = 1
            elif any(city in message_lower for city in ["pune", "jaipur", "lucknow", "chandigarh", "kochi"]):
                app_data["city_tier"] = 2

            # Fallback parse for mixed messages (e.g., "tier2 city, 40 moths, 100000")
            all_numbers = [int(value) for value in re.findall(r'\b\d{1,8}\b', message)]
            is_composite_input = (
                len(all_numbers) >= 2
                or "," in message
                or any(token in message_lower for token in ["tier", "month", "months", "moth", "moths", "tenure"])
            )
            if all_numbers and is_composite_input:
                if not app_data.get("city_tier") and any("tier" in token for token in message_lower.split()):
                    tier_candidates = [n for n in all_numbers if n in (1, 2, 3)]
                    if tier_candidates:
                        app_data["city_tier"] = tier_candidates[0]

                if not app_data.get("tenure_months") and any(word in message_lower for word in ["month", "months", "moth", "moths", "tenure", "period"]):
                    tenure_candidates = [n for n in all_numbers if 6 <= n <= 360]
                    if tenure_candidates:
                        app_data["tenure_months"] = tenure_candidates[0]

                if not app_data.get("requested_amount"):
                    amount_candidates = [n for n in all_numbers if 10000 <= n <= 50000000]
                    if amount_candidates:
                        app_data["requested_amount"] = float(max(amount_candidates))
            
            state["application_data"] = app_data
        
        if state["stage"] in ["completed", "rejected"]:
            follow_up_reply = generate_follow_up_response(state, message)
            state["messages"].append({
                "role": "assistant",
                "content": follow_up_reply,
                "timestamp": datetime.now().isoformat()
            })
            result_state = state
        elif state["stage"] == "await_acceptance":
            if is_acceptance_message and not is_rejection_message:
                state["is_accepted"] = True
                state = handle_acceptance_node(state)
                result_state = run_workflow_stepwise(state)
            elif is_rejection_message:
                state["is_accepted"] = False
                result_state = handle_acceptance_node(state)
            else:
                follow_up_reply = generate_follow_up_response(state, message)
                state["messages"].append({
                    "role": "assistant",
                    "content": follow_up_reply,
                    "timestamp": datetime.now().isoformat()
                })
                result_state = state
        elif state["stage"] == "collect_info":
            has_all_required = all(
                state["application_data"].get(field) not in (None, "")
                for field in REQUIRED_APPLICATION_FIELDS
            )

            if has_all_required and is_acceptance_message:
                state["stage"] = "verify_kyc"
                result_state = run_workflow_stepwise(state)
            else:
                result_state = run_workflow_stepwise(state)
        elif state["stage"] in STEP_CONFIRMATION_STAGES:
            if is_continue_message or is_acceptance_message:
                result_state = run_workflow_stepwise(state)
            else:
                state["messages"].append({
                    "role": "assistant",
                    "content": "Reply 'ok' to continue to the next stage.",
                    "timestamp": datetime.now().isoformat()
                })
                result_state = state
        else:
            result_state = run_workflow_stepwise(state)
        
        # Update database
        update_doc = {
            "workflow_stage": result_state["stage"],
            "application_data": result_state["application_data"],
            "kyc_data": result_state.get("kyc_data"),
            "credit_data": result_state.get("credit_data"),
            "policy_validation": result_state.get("policy_validation"),
            "affordability_result": result_state.get("affordability_result"),
            "risk_assessment": result_state.get("risk_assessment"),
            "loan_offer": result_state.get("loan_offer"),
            "emi_schedule": result_state.get("emi_schedule"),
            "loan_id": result_state.get("loan_id"),
            "sanction_letter_path": result_state.get("sanction_letter_path"),
            "conversation_messages": result_state["messages"],
            "is_eligible": result_state["is_eligible"],
            "is_accepted": result_state["is_accepted"],
            "rejection_reason": result_state.get("rejection_reason"),
            "updated_at": result_state["updated_at"]
        }
        
        # Update status
        if result_state["stage"] == "completed":
            if result_state["loan_id"]:
                update_doc["status"] = "APPROVED"
            else:
                update_doc["status"] = "DECLINED"
        elif result_state["stage"] == "rejected":
            update_doc["status"] = "REJECTED"
        else:
            update_doc["status"] = "IN_PROGRESS"

        update_doc["progress"] = _build_pipeline_progress(result_state, update_doc["status"])
        
        await mongodb.loan_applications.update_one(
            {"application_id": application_id},
            {"$set": update_doc}
        )
        
        # If loan was created, save to loans collection
        if result_state.get("loan_id") and not app_doc.get("loan_id"):
            loan_doc = {
                "loan_id": result_state["loan_id"],
                "application_id": application_id,
                "user_id": current_user.user_id,
                "loan_type": result_state["loan_type"],
                "principal": result_state["loan_offer"]["principal"],
                "tenure_months": result_state["loan_offer"]["tenure_months"],
                "interest_rate": result_state["loan_offer"]["interest_rate"],
                "monthly_emi": result_state["loan_offer"]["monthly_emi"],
                "total_interest": result_state["loan_offer"]["total_interest"],
                "total_repayment": result_state["loan_offer"]["total_repayment"],
                "status": "ACTIVE",
                "disbursement_date": datetime.now().isoformat(),
                "disbursement_amount": result_state["loan_offer"]["net_disbursement"],
                "sanction_letter_url": f"/api/loans/{result_state['loan_id']}/sanction-letter",
                "emi_schedule": result_state["emi_schedule"]["schedule"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            await mongodb.loans.insert_one(loan_doc)
            logger.info(f"Loan {result_state['loan_id']} created and disbursed")
        
        logger.info(f"Chat processed for application {application_id}, stage: {result_state['stage']}")
        
        return {
            "application_id": application_id,
            "stage": result_state["stage"],
            "status": update_doc["status"],
            "messages": result_state["messages"],
            "loan_offer": result_state.get("loan_offer"),
            "emi_schedule": result_state.get("emi_schedule"),
            "loan_id": result_state.get("loan_id"),
            "progress": _build_pipeline_progress(result_state, update_doc["status"]),
            "completed": result_state["stage"] in ["completed", "rejected"]
        }
        
    except Exception as e:
        logger.error(f"Error in chat workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/applications")
async def list_applications(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    List all loan applications for current user
    
    Args:
        status: Filter by status (optional)
        current_user: Authenticated user
    
    Returns:
        List of applications
    """
    try:
        query = {"user_id": current_user.user_id}
        if status:
            query["status"] = status.upper()
        
        cursor = mongodb.loan_applications.find(query).sort("created_at", -1)
        applications = await cursor.to_list(length=100)
        
        # Remove MongoDB _id
        for app in applications:
            app.pop("_id", None)
        
        logger.info(f"Retrieved {len(applications)} applications for user {current_user.user_id}")
        
        return {"applications": applications}
        
    except Exception as e:
        logger.error(f"Error listing applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applications: {str(e)}"
        )


@router.get("/applications/{application_id}")
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed application information
    
    Args:
        application_id: Application ID
        current_user: Authenticated user
    
    Returns:
        Complete application details
    """
    try:
        app_doc = await mongodb.loan_applications.find_one({
            "application_id": application_id,
            "user_id": current_user.user_id
        })
        
        if not app_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        app_doc.pop("_id", None)
        
        return app_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch application: {str(e)}"
        )


@router.get("/active")
async def get_active_loans(
    current_user: User = Depends(get_current_user)
):
    """
    Get all active loans for current user
    
    Args:
        current_user: Authenticated user
    
    Returns:
        List of active loans
    """
    try:
        cursor = mongodb.loans.find({
            "user_id": current_user.user_id,
            "status": "ACTIVE"
        }).sort("created_at", -1)
        
        loans = await cursor.to_list(length=50)
        
        for loan in loans:
            loan.pop("_id", None)
        
        logger.info(f"Retrieved {len(loans)} active loans for user {current_user.user_id}")
        
        return {"loans": loans}
        
    except Exception as e:
        logger.error(f"Error fetching active loans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch loans: {str(e)}"
        )


@router.get("/{loan_id}")
async def get_loan_details(
    loan_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed loan information
    
    Args:
        loan_id: Loan ID
        current_user: Authenticated user
    
    Returns:
        Complete loan details
    """
    try:
        loan_doc = await mongodb.loans.find_one({
            "loan_id": loan_id,
            "user_id": current_user.user_id
        })
        
        if not loan_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        loan_doc.pop("_id", None)
        
        return loan_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching loan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch loan: {str(e)}"
        )


@router.get("/{loan_id}/emi-schedule")
async def get_emi_schedule(
    loan_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get EMI schedule for a loan
    
    Args:
        loan_id: Loan ID
        current_user: Authenticated user
    
    Returns:
        Complete EMI schedule
    """
    try:
        loan_doc = await mongodb.loans.find_one({
            "loan_id": loan_id,
            "user_id": current_user.user_id
        })
        
        if not loan_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        emi_schedule = loan_doc.get("emi_schedule", [])
        
        # Calculate summary
        total_paid = sum(
            inst["emi_amount"] for inst in emi_schedule 
            if inst.get("status") == "PAID"
        )
        total_pending = sum(
            inst["emi_amount"] for inst in emi_schedule 
            if inst.get("status") == "PENDING"
        )
        
        return {
            "loan_id": loan_id,
            "schedule": emi_schedule,
            "summary": {
                "total_installments": len(emi_schedule),
                "paid_installments": sum(1 for inst in emi_schedule if inst.get("status") == "PAID"),
                "pending_installments": sum(1 for inst in emi_schedule if inst.get("status") == "PENDING"),
                "total_paid": total_paid,
                "total_pending": total_pending
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching EMI schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch EMI schedule: {str(e)}"
        )


@router.get("/{loan_id}/sanction-letter")
async def download_sanction_letter(
    loan_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download sanction letter PDF
    
    Args:
        loan_id: Loan ID
        current_user: Authenticated user
    
    Returns:
        PDF file
    """
    from fastapi.responses import FileResponse
    import os
    
    try:
        loan_doc = await mongodb.loans.find_one({
            "loan_id": loan_id,
            "user_id": current_user.user_id
        })
        
        if not loan_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        # Get sanction letter from application
        app_doc = await mongodb.loan_applications.find_one({
            "loan_id": loan_id,
            "user_id": current_user.user_id
        })
        
        if not app_doc or not app_doc.get("sanction_letter_path"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sanction letter not found"
            )
        
        file_path = app_doc["sanction_letter_path"]
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sanction letter file not found"
            )
        
        logger.info(f"Sanction letter downloaded for loan {loan_id}")
        
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"sanction_letter_{loan_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading sanction letter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download sanction letter: {str(e)}"
        )
