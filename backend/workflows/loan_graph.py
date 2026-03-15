"""
LangGraph Loan Application Workflow
Stateful workflow orchestration using LangGraph
"""

from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import logging
from datetime import datetime
import json
import uuid

from workflows.tools import ALL_TOOLS
from workflows.prompts import PROMPTS
from config import settings

logger = logging.getLogger(__name__)


REQUIRED_APPLICATION_FIELDS = [
    "aadhaar",
    "pan",
    "monthly_income",
    "requested_amount",
    "tenure_months",
    "age",
    "employment_type",
    "employment_years",
    "city_tier",
]


def _missing_application_fields(application_data: Dict[str, Any]) -> List[str]:
    return [field for field in REQUIRED_APPLICATION_FIELDS if not application_data.get(field)]


def _safe_application_context(application_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in application_data.items()
        if key not in {"aadhaar", "pan"}
    }


def _build_offer_prompt_context(offer: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "principal": offer.get("principal", 0),
        "tenure": offer.get("tenure_months", 0),
        "interest_rate": offer.get("interest_rate", 0),
        "monthly_emi": offer.get("monthly_emi", 0),
        "processing_fee": offer.get("total_processing_fee", offer.get("processing_fee", 0)),
        "total_interest": offer.get("total_interest", 0),
        "total_repayment": offer.get("total_repayment", 0),
        "net_disbursement": offer.get("net_disbursement", 0),
    }


def _add_assistant_message(state: "LoanWorkflowState", content: str) -> None:
    state["messages"].append({
        "role": "assistant",
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })


# Define workflow state
class LoanWorkflowState(TypedDict):
    """State maintained throughout loan application workflow"""
    
    # Identifiers
    application_id: str
    user_id: str
    loan_type: str
    
    # Current stage
    stage: Literal[
        "init",
        "collect_info",
        "verify_kyc",
        "fetch_credit",
        "check_policy",
        "assess_affordability",
        "assess_risk",
        "generate_offer",
        "explain_offer",
        "await_acceptance",
        "generate_sanction",
        "simulate_disbursement",
        "rejected",
        "completed"
    ]
    
    # Application data
    application_data: Dict[str, Any]
    
    # Verification data
    kyc_data: Optional[Dict[str, Any]]
    credit_data: Optional[Dict[str, Any]]
    
    # Assessment results
    policy_validation: Optional[Dict[str, Any]]
    affordability_result: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    
    # Offer
    loan_offer: Optional[Dict[str, Any]]
    emi_schedule: Optional[Dict[str, Any]]
    
    # Loan details (after acceptance)
    loan_id: Optional[str]
    sanction_letter_path: Optional[str]
    
    # Conversation history
    messages: List[Dict[str, str]]
    
    # Decision flags
    is_eligible: bool
    is_accepted: bool
    rejection_reason: Optional[str]
    
    # Metadata
    created_at: str
    updated_at: str


# Initialize LLM with Groq (fast, generous free tier)
llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # Latest Llama 3.3 model
    temperature=0.3,
    groq_api_key=settings.GROQ_API_KEY,
    max_retries=2
)


# Node functions

def init_application(state: LoanWorkflowState) -> LoanWorkflowState:
    """Initialize application state"""
    state["stage"] = "collect_info"
    state["is_eligible"] = True
    state["is_accepted"] = False
    state["created_at"] = datetime.now().isoformat()
    state["updated_at"] = datetime.now().isoformat()
    
    if not state["messages"]:
        welcome_msg = (
            f"Welcome! Let's help you apply for a {state['loan_type'].replace('_', ' ')}. "
            "I'll guide you through the process."
        )
        state["messages"].append({
            "role": "assistant",
            "content": welcome_msg
        })
    
    logger.info(f"Application {state['application_id']} initialized")
    return state


def collect_information(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    LLM node: Collect application information from user
    Uses conversational interface to gather all required data
    """
    application_context = _safe_application_context(state.get("application_data", {}))
    missing_fields = _missing_application_fields(state.get("application_data", {}))

    if not missing_fields:
        _add_assistant_message(
            state,
            "All required details received. Reply 'yes' to start KYC verification.",
        )
        state["updated_at"] = datetime.now().isoformat()
        logger.info(f"Collection complete for {state['application_id']}; moving to verification")
        return state

    system_prompt = PROMPTS["collect_info"].format(loan_type=state["loan_type"]) + (
        "\n\nCONVERSATION RULES:\n"
        "- The customer has already been greeted. Do not greet them again.\n"
        "- Continue from the current conversation only.\n"
        f"- Already collected fields: {', '.join(sorted(application_context.keys())) or 'none'}.\n"
        f"- Missing required fields: {', '.join(missing_fields) or 'none'}.\n"
        "- Ask only for the next most important missing detail.\n"
        "- If all required fields are available, confirm that verification is starting."
    )
    
    # Build message history
    messages = [SystemMessage(content=system_prompt)]
    for msg in state["messages"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    
    # Get LLM response
    response = llm.invoke(messages)
    
    # Add to conversation
    state["messages"].append({
        "role": "assistant",
        "content": response.content
    })
    
    state["updated_at"] = datetime.now().isoformat()
    
    # Check if ready to proceed (this would be determined by parsing user responses)
    # For now, assume collection is done when application_data is populated
    
    logger.info(f"Information collection step for {state['application_id']}")
    return state


def verify_kyc_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Verify KYC documents
    """
    app_data = state["application_data"]
    
    try:
        # Call KYC verification tool
        from workflows.tools import verify_kyc
        
        result = verify_kyc.invoke({
            "aadhaar": app_data["aadhaar"],
            "pan": app_data["pan"],
            "user_id": state["user_id"]
        })
        
        state["kyc_data"] = result

        if result.get("kyc_status") == "VERIFIED":
            state["stage"] = "fetch_credit"
            aadhaar_masked = ((result.get("aadhaar") or {}).get("masked") or "XXXX-XXXX-XXXX")
            pan_masked = ((result.get("pan") or {}).get("masked") or "XX***XXX")
            aadhaar_token = (result.get("encrypted_aadhaar") or "")[-8:] or "encrypted"
            pan_token = (result.get("encrypted_pan") or "")[-8:] or "encrypted"
            applicant_name = result.get("applicant_name") or "Verified Applicant"
            _add_assistant_message(
                state,
                (
                    "KYC verification completed through mock UIDAI/PAN APIs.\n"
                    f"• Applicant: {applicant_name}\n"
                    f"• Aadhaar: {aadhaar_masked}\n"
                    f"• PAN: {pan_masked}\n"
                    f"• Encrypted Aadhaar Token: ****{aadhaar_token}\n"
                    f"• Encrypted PAN Token: ****{pan_token}\n"
                    "Reply 'ok' to continue to Credit Bureau Check."
                ),
            )
        else:
            state["is_eligible"] = False
            state["rejection_reason"] = result.get("reason", "KYC verification failed")
            state["stage"] = "rejected"

        logger.info(f"KYC verification: {result.get('kyc_status')}")
        
    except Exception as e:
        logger.error(f"KYC verification error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"KYC verification error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def fetch_credit_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Fetch credit report
    """
    try:
        from workflows.tools import fetch_credit_report

        app_data = state["application_data"]
        result = fetch_credit_report.invoke({
            "pan": app_data["pan"]  # Use original PAN for credit lookup
        })
        
        state["credit_data"] = result
        profile_name = result.get("name") or "Verified Applicant"
        
        # Check minimum credit score
        if result.get("credit_score", 0) < 700:
            state["is_eligible"] = False
            state["rejection_reason"] = f"Credit score {result.get('credit_score')} below minimum requirement"
            state["stage"] = "rejected"
        else:
            state["stage"] = "check_policy"
        _add_assistant_message(
            state,
            (
                "Credit assessment completed using mock bureau/CIBIL dataset. "
                f"Name match: {profile_name}. "
                f"Credit score: {result.get('credit_score', 'N/A')}. "
                "Reply 'ok' to continue to Policy Validation."
            ),
        )
        
        logger.info(f"Credit fetched: score {result.get('credit_score')}")
        
    except Exception as e:
        logger.error(f"Credit fetch error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"Credit fetch error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def check_policy_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Validate against policy rules
    """
    try:
        from workflows.tools import validate_policy_eligibility
        
        app_data = state["application_data"]
        credit_data = state["credit_data"]
        
        result = validate_policy_eligibility.invoke({
            "loan_type": state["loan_type"],
            "age": app_data.get("age", 30),
            "credit_score": credit_data["credit_score"],
            "monthly_income": app_data["monthly_income"],
            "employment_type": app_data.get("employment_type", "salaried"),
            "requested_amount": app_data["requested_amount"],
            "tenure_months": app_data["tenure_months"],
            "existing_emi": credit_data.get("existing_emi", 0),
            "active_loans": credit_data.get("active_loans", 0),
            "dpd_30_days": credit_data.get("dpd_30_days", 0)
        })
        
        state["policy_validation"] = result
        
        if result["is_eligible"]:
            state["stage"] = "assess_affordability"
            _add_assistant_message(
                state,
                "Policy validation passed. Reply 'ok' to continue to Affordability Analysis.",
            )
        else:
            state["is_eligible"] = False
            state["rejection_reason"] = f"Policy violations: {', '.join(result['violations'])}"
            state["stage"] = "rejected"
        
        logger.info(f"Policy check: eligible={result['is_eligible']}")
        
    except Exception as e:
        logger.error(f"Policy check error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"Policy check error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def assess_affordability_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Calculate affordability
    """
    try:
        from workflows.tools import calculate_affordability
        
        app_data = state["application_data"]
        credit_data = state["credit_data"]
        
        # Get base interest rate for calculation
        from engines.policy_engine import policy_engine
        base_rate = policy_engine.get_interest_rate(state["loan_type"], "MEDIUM", app_data)
        
        result = calculate_affordability.invoke({
            "monthly_income": app_data["monthly_income"],
            "existing_emi": credit_data["existing_emi"],
            "requested_amount": app_data["requested_amount"],
            "interest_rate": base_rate,
            "tenure_months": app_data["tenure_months"],
            "foir_limit": 0.60
        })
        
        state["affordability_result"] = result
        
        if result["status"] in ["APPROVED", "REDUCED"]:
            # Update application amount if reduced
            if result["status"] == "REDUCED":
                app_data["final_amount"] = result["eligible_amount"]
            else:
                app_data["final_amount"] = app_data["requested_amount"]
            
            state["stage"] = "assess_risk"
            _add_assistant_message(
                state,
                (
                    f"Affordability analysis complete: status {result['status']}. "
                    f"Eligible amount: ₹{result.get('eligible_amount', 0):,.0f}. "
                    "Reply 'ok' to continue to Risk Scoring."
                ),
            )
        else:
            state["is_eligible"] = False
            state["rejection_reason"] = "Requested amount not affordable"
            state["stage"] = "rejected"
        
        logger.info(f"Affordability: {result['status']}, eligible={result['eligible_amount']}")
        
    except Exception as e:
        logger.error(f"Affordability error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"Affordability error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def assess_risk_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Perform risk assessment
    """
    try:
        from workflows.tools import assess_risk
        
        app_data = state["application_data"]
        credit_data = state["credit_data"]
        affordability = state["affordability_result"]
        
        result = assess_risk.invoke({
            "credit_score": credit_data["credit_score"],
            "foir": affordability["foir_requested"],
            "employment_type": app_data.get("employment_type", "salaried"),
            "employment_years": app_data.get("employment_years", 2),
            "city_tier": app_data.get("city_tier", 2),
            "existing_emi": credit_data.get("existing_emi", 0),
            "monthly_income": app_data["monthly_income"],
            "active_loans": credit_data.get("active_loans", 0),
            "dpd_30_days": credit_data.get("dpd_30_days", 0),
            "bureau_flags": credit_data.get("bureau_flags", [])
        })
        
        state["risk_assessment"] = result
        state["stage"] = "generate_offer"
        _add_assistant_message(
            state,
            (
                f"Risk scoring complete. Segment: {result.get('risk_segment', 'N/A')} "
                f"(score: {result.get('risk_score', 0):.2f}). Reply 'ok' to generate final offer."
            ),
        )
        
        logger.info(f"Risk assessed: score={result['risk_score']:.2f}, segment={result['risk_segment']}")
        
    except Exception as e:
        logger.error(f"Risk assessment error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"Risk assessment error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def generate_offer_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Generate loan offer
    """
    try:
        from workflows.tools import generate_loan_offer, generate_emi_schedule
        
        app_data = state["application_data"]
        risk_data = state["risk_assessment"]
        
        # Generate offer
        offer = generate_loan_offer.invoke({
            "loan_type": state["loan_type"],
            "principal": app_data.get("final_amount", app_data["requested_amount"]),
            "tenure_months": app_data["tenure_months"],
            "risk_segment": risk_data["risk_segment"],
            "age": app_data.get("age", 30),
            "employment_type": app_data.get("employment_type", "salaried"),
            "city_tier": app_data.get("city_tier", 2)
        })
        
        # Generate EMI schedule
        emi_schedule = generate_emi_schedule.invoke({
            "principal": offer["principal"],
            "interest_rate": offer["interest_rate"],
            "tenure_months": offer["tenure_months"],
            "disbursement_date": datetime.now().isoformat()
        })
        
        state["loan_offer"] = offer
        state["emi_schedule"] = emi_schedule
        state["stage"] = "explain_offer"
        
        logger.info(f"Offer generated: ₹{offer['principal']} @ {offer['interest_rate']}%")
        
    except Exception as e:
        logger.error(f"Offer generation error: {str(e)}")
        state["is_eligible"] = False
        state["rejection_reason"] = f"Offer generation error: {str(e)}"
        state["stage"] = "rejected"
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def explain_offer_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    LLM node: Explain loan offer to customer
    """
    offer = state["loan_offer"]
    
    _add_assistant_message(
        state,
        (
            "Loan offer generated successfully.\n"
            f"• Amount: ₹{offer.get('principal', 0):,.0f}\n"
            f"• Tenure: {offer.get('tenure_months', 0)} months\n"
            f"• Rate: {offer.get('interest_rate', 0)}% p.a.\n"
            f"• EMI: ₹{offer.get('monthly_emi', 0):,.0f}\n"
            f"• Net disbursement: ₹{offer.get('net_disbursement', 0):,.0f}\n\n"
            "Reply with 'accept' to proceed to sanction letter and disbursement simulation, or 'reject' to decline."
        ),
    )
    
    state["stage"] = "await_acceptance"
    state["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Offer explained to customer")
    return state


def generate_follow_up_response(state: LoanWorkflowState, user_message: str) -> str:
    """
    Answer follow-up questions without mutating the underwriting decision.
    Used for offer clarifications and post-completion chat.
    """
    context = {
        "stage": state["stage"],
        "application_id": state["application_id"],
        "loan_type": state["loan_type"],
        "application_data": _safe_application_context(state.get("application_data", {})),
        "credit_score": (state.get("credit_data") or {}).get("credit_score"),
        "risk_segment": (state.get("risk_assessment") or {}).get("risk_segment"),
        "loan_offer": state.get("loan_offer"),
        "loan_id": state.get("loan_id"),
        "sanction_letter_ready": bool(state.get("sanction_letter_path")),
        "is_completed": state["stage"] == "completed",
        "is_accepted": state.get("is_accepted", False),
    }

    system_prompt = PROMPTS["base"] + """

CURRENT STAGE: Customer Follow-up

Your task:
1. Answer the customer's question using the provided application context.
2. Do not restart the application or repeat the welcome message.
3. Do not alter approval, rejection, or loan terms unless the customer's message is an explicit acceptance or rejection handled elsewhere.
4. If the sanction letter is already available, mention that it can be downloaded from the loan details page.
5. Keep the answer concise, clear, and specific to the customer's current application.
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Application context:\n{json.dumps(context, default=str, indent=2)}\n\n"
                f"Customer question: {user_message}"
            )
        )
    ])

    return response.content


def run_workflow_until_pause(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Execute the workflow from the state's current stage until user input is needed again.
    This avoids re-entering the graph from the init node for every chat message.
    """
    while True:
        current_stage = state["stage"]

        if current_stage == "init":
            state = init_application(state)
            continue

        if current_stage == "collect_info":
            state = collect_information(state)
            next_stage = should_continue_after_info(state)
            if next_stage == END:
                state["stage"] = "collect_info"
                return state
            state["stage"] = next_stage
            continue

        if current_stage == "verify_kyc":
            state = verify_kyc_node(state)
            continue

        if current_stage == "fetch_credit":
            state = fetch_credit_node(state)
            continue

        if current_stage == "check_policy":
            state = check_policy_node(state)
            continue

        if current_stage == "assess_affordability":
            state = assess_affordability_node(state)
            continue

        if current_stage == "assess_risk":
            state = assess_risk_node(state)
            continue

        if current_stage == "generate_offer":
            state = generate_offer_node(state)
            continue

        if current_stage == "explain_offer":
            state = explain_offer_node(state)
            return state

        if current_stage == "await_acceptance":
            return state

        if current_stage == "generate_sanction":
            state = generate_sanction_node(state)
            continue

        if current_stage == "simulate_disbursement":
            state = simulate_disbursement_node(state)
            return state

        if current_stage == "rejected":
            state = handle_rejection_node(state)
            return state

        if current_stage == "completed":
            return state

        logger.warning(f"Unknown workflow stage encountered: {current_stage}")
        return state


def run_workflow_stepwise(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Execute exactly one workflow step and then pause.
    This enables explicit customer confirmation between stages.
    """
    current_stage = state["stage"]

    if current_stage == "init":
        return init_application(state)

    if current_stage == "collect_info":
        state = collect_information(state)
        next_stage = should_continue_after_info(state)
        if next_stage != END:
            state["stage"] = next_stage
        return state

    if current_stage == "verify_kyc":
        state = verify_kyc_node(state)
    elif current_stage == "fetch_credit":
        state = fetch_credit_node(state)
    elif current_stage == "check_policy":
        state = check_policy_node(state)
    elif current_stage == "assess_affordability":
        state = assess_affordability_node(state)
    elif current_stage == "assess_risk":
        state = assess_risk_node(state)
    elif current_stage == "generate_offer":
        state = generate_offer_node(state)
        if state.get("stage") == "explain_offer":
            state = explain_offer_node(state)
    elif current_stage == "explain_offer":
        state = explain_offer_node(state)
    elif current_stage == "generate_sanction":
        state = generate_sanction_node(state)
    elif current_stage == "simulate_disbursement":
        state = simulate_disbursement_node(state)
    elif current_stage == "rejected":
        state = handle_rejection_node(state)
    elif current_stage in {"await_acceptance", "completed"}:
        return state
    else:
        logger.warning(f"Unknown workflow stage encountered: {current_stage}")
        return state

    if state.get("stage") == "rejected":
        state = handle_rejection_node(state)

    return state


def handle_acceptance_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Decision node: Handle customer's acceptance/rejection
    This is typically triggered by user input
    """
    if state["is_accepted"]:
        state["stage"] = "generate_sanction"
        state["loan_id"] = str(uuid.uuid4())
        _add_assistant_message(
            state,
            "Offer accepted. Handing over to Sanction Letter Agent to generate your structured PDF.",
        )
    else:
        state["stage"] = "completed"
        _add_assistant_message(
            state,
            "Offer declined. Application has been closed. You can start a new application anytime.",
        )
    
    state["updated_at"] = datetime.now().isoformat()
    logger.info(f"Acceptance handled: {state['is_accepted']}")
    return state


def generate_sanction_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Tool node: Generate sanction letter
    """
    try:
        from workflows.tools import generate_sanction_letter
        
        result = generate_sanction_letter.invoke({
            "loan_id": state["loan_id"],
            "application_data": state["application_data"],
            "offer_data": state["loan_offer"],
            "user_data": {"user_id": state["user_id"], "email": state["application_data"].get("email", "customer@example.com")},
            "emi_summary": state["emi_schedule"]["summary"]
        })
        
        state["sanction_letter_path"] = result["file_path"]
        state["stage"] = "simulate_disbursement"
        _add_assistant_message(
            state,
            "Sanction letter generated successfully. Reply 'ok' to complete disbursement simulation.",
        )
        
        logger.info(f"Sanction letter generated: {result['file_path']}")
        
    except Exception as e:
        logger.error(f"Sanction generation error: {str(e)}")
        state["messages"].append({
            "role": "assistant",
            "content": f"There was an issue generating your sanction letter. Please contact support. Error: {str(e)}"
        })
    
    state["updated_at"] = datetime.now().isoformat()
    return state


def simulate_disbursement_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    LLM node: Simulate disbursement process
    """
    _add_assistant_message(
        state,
        (
            "Disbursement simulation completed.\n"
            f"• Loan ID: {state['loan_id']}\n"
            f"• Disbursement amount: ₹{state['loan_offer']['net_disbursement']:,.0f}\n"
            "• Expected credit timeline: 2-3 business days\n"
            "Your chat is saved and sanction letter is available from loan details."
        ),
    )
    
    state["stage"] = "completed"
    state["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Disbursement simulated for loan {state['loan_id']}")
    return state


def handle_rejection_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    LLM node: Handle application rejection
    """
    system_prompt = PROMPTS["rejection"]
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Application rejected: {state['rejection_reason']}")
    ]
    
    response = llm.invoke(messages)
    
    state["messages"].append({
        "role": "assistant",
        "content": response.content
    })
    
    state["stage"] = "completed"
    state["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Rejection handled: {state['rejection_reason']}")
    return state


# Define conditional edges

def should_continue_after_info(state: LoanWorkflowState) -> str:
    """Check if enough information collected"""
    # Check if we have all required fields
    app_data = state.get("application_data", {})
    required_fields = REQUIRED_APPLICATION_FIELDS

    missing_fields = [f for f in required_fields if f not in app_data]
    if not missing_fields:
        logger.info("All required fields collected, awaiting explicit customer confirmation for KYC")
        return END

    # Otherwise, stop and wait for more user input
    # Don't loop back to collect_info - that will trigger LLM again
    logger.info(f"Missing fields: {missing_fields}, waiting for user input")
    return END


def should_continue_after_kyc(state: LoanWorkflowState) -> str:
    """Route based on KYC result"""
    if state["is_eligible"]:
        return "fetch_credit"
    return "rejected"


def should_continue_after_credit(state: LoanWorkflowState) -> str:
    """Route based on credit check"""
    if state["is_eligible"]:
        return "check_policy"
    return "rejected"


def should_continue_after_policy(state: LoanWorkflowState) -> str:
    """Route based on policy validation"""
    if state["is_eligible"]:
        return "assess_affordability"
    return "rejected"


def should_continue_after_affordability(state: LoanWorkflowState) -> str:
    """Route based on affordability"""
    if state["is_eligible"]:
        return "assess_risk"
    return "rejected"


def should_continue_after_acceptance(state: LoanWorkflowState) -> str:
    """Route based on customer decision"""
    if state["is_accepted"]:
        return "generate_sanction"
    return END


# Build the workflow graph

def create_loan_workflow() -> StateGraph:
    """
    Create and compile the loan workflow graph
    """
    workflow = StateGraph(LoanWorkflowState)
    
    # Add all nodes
    workflow.add_node("init", init_application)
    workflow.add_node("collect_info", collect_information)
    workflow.add_node("verify_kyc", verify_kyc_node)
    workflow.add_node("fetch_credit", fetch_credit_node)
    workflow.add_node("check_policy", check_policy_node)
    workflow.add_node("assess_affordability", assess_affordability_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("generate_offer", generate_offer_node)
    workflow.add_node("explain_offer", explain_offer_node)
    workflow.add_node("handle_acceptance", handle_acceptance_node)
    workflow.add_node("generate_sanction", generate_sanction_node)
    workflow.add_node("simulate_disbursement", simulate_disbursement_node)
    workflow.add_node("rejected", handle_rejection_node)
    
    # Set entry point
    workflow.set_entry_point("init")
    
    # Add edges
    workflow.add_edge("init", "collect_info")
    workflow.add_conditional_edges("collect_info", should_continue_after_info)
    workflow.add_conditional_edges("verify_kyc", should_continue_after_kyc)
    workflow.add_conditional_edges("fetch_credit", should_continue_after_credit)
    workflow.add_conditional_edges("check_policy", should_continue_after_policy)
    workflow.add_conditional_edges("assess_affordability", should_continue_after_affordability)
    workflow.add_edge("assess_risk", "generate_offer")
    workflow.add_edge("generate_offer", "explain_offer")
    workflow.add_edge("explain_offer", "handle_acceptance")
    workflow.add_conditional_edges("handle_acceptance", should_continue_after_acceptance)
    workflow.add_edge("generate_sanction", "simulate_disbursement")
    workflow.add_edge("simulate_disbursement", END)
    workflow.add_edge("rejected", END)
    
    # Compile
    return workflow.compile()


# Global compiled graph
loan_workflow = create_loan_workflow()

logger.info("Loan workflow graph created successfully")
