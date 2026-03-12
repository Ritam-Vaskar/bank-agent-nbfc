"""
Loan Application Routes
Integrates LangGraph workflow with HTTP endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime
import logging
import uuid

from auth.dependencies import get_current_user
from models.user import User
from models.loan_application import LoanApplication, ApplicationData, ConversationMessage, ChatMessage
from models.loan import Loan
from database import mongodb, redis_client
from workflows.loan_graph import loan_workflow, LoanWorkflowState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("/apply")
async def start_loan_application(
    loan_type: str,
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
        result_state = loan_workflow.invoke(
            initial_state,
            config={"recursion_limit": 5}
        )
        
        # Save application to database
        application_doc = {
            "application_id": application_id,
            "user_id": current_user.user_id,
            "loan_type": loan_type,
            "status": "IN_PROGRESS",
            "workflow_stage": result_state["stage"],
            "application_data": result_state["application_data"],
            "conversation_messages": result_state["messages"],
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
            "stage": result_state["stage"],
            "messages": result_state["messages"]
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
        
        # Check if workflow is already completed
        if app_doc["workflow_stage"] in ["completed", "rejected"]:
            return {
                "application_id": application_id,
                "stage": app_doc["workflow_stage"],
                "messages": app_doc["conversation_messages"],
                "completed": True
            }
        
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
        
        # Parse message for special commands (acceptance, data extraction, etc.)
        message_lower = message.lower()
        
        # Check for acceptance/rejection
        if state["stage"] == "await_acceptance":
            if any(word in message_lower for word in ["accept", "yes", "proceed", "agree"]):
                state["is_accepted"] = True
            elif any(word in message_lower for word in ["reject", "no", "decline", "cancel"]):
                state["is_accepted"] = False
        
        # Parse application data if in collection stage
        if state["stage"] == "collect_info":
            # Extract data from message (simple keyword matching)
            # In production, use better NLP or structured forms
            app_data = state["application_data"]
            
            # Extract Aadhaar
            import re
            aadhaar_match = re.search(r'\b\d{12}\b', message)
            if aadhaar_match:
                app_data["aadhaar"] = aadhaar_match.group()
            
            # Extract PAN
            pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', message)
            if pan_match:
                app_data["pan"] = pan_match.group()
            
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
            
            # Extract tenure
            if any(word in message_lower for word in ["month", "tenure", "period", "year"]):
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
            
            # Extract city tier
            if "tier" in message_lower:
                tier_match = re.search(r'\b([123])\b', message)
                if tier_match:
                    app_data["city_tier"] = int(tier_match.group())
            elif any(city in message_lower for city in ["mumbai", "delhi", "bangalore", "chennai", "kolkata", "hyderabad"]):
                app_data["city_tier"] = 1
            elif any(city in message_lower for city in ["pune", "jaipur", "lucknow", "chandigarh", "kochi"]):
                app_data["city_tier"] = 2
            else:
                if not app_data.get("city_tier"):
                    app_data["city_tier"] = 3  # Default
            
            # Default employment years if not provided
            if not app_data.get("employment_years"):
                app_data["employment_years"] = 2  # Default assumption
            
            state["application_data"] = app_data
        
        # Run workflow with updated state
        # Use recursion_limit to prevent infinite loops
        result_state = loan_workflow.invoke(
            state,
            config={"recursion_limit": 10}
        )
        
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
            "messages": result_state["messages"],
            "loan_offer": result_state.get("loan_offer"),
            "emi_schedule": result_state.get("emi_schedule"),
            "loan_id": result_state.get("loan_id"),
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
            "loan_id": loan_id
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
