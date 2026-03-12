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
import uuid

from workflows.tools import ALL_TOOLS
from workflows.prompts import PROMPTS
from config import settings

logger = logging.getLogger(__name__)


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
    
    # Add welcome message
    welcome_msg = f"Welcome! Let's help you apply for a {state['loan_type'].replace('_', ' ')}. I'll guide you through the process."
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
    system_prompt = PROMPTS["collect_info"].format(loan_type=state["loan_type"])
    
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
        
        if result.get("aadhaar_verified") and result.get("pan_verified"):
            state["stage"] = "fetch_credit"
            
            # LLM explanation
            system_prompt = PROMPTS["explain_kyc"]
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"KYC result: {result}")
            ]
            response = llm.invoke(messages)
            
            state["messages"].append({
                "role": "assistant",
                "content": response.content
            })
        else:
            state["is_eligible"] = False
            state["rejection_reason"] = "KYC verification failed"
            state["stage"] = "rejected"
        
        logger.info(f"KYC verification: {result.get('aadhaar_verified')} / {result.get('pan_verified')}")
        
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
        
        kyc_data = state["kyc_data"]
        result = fetch_credit_report.invoke({
            "pan": kyc_data["pan_masked"]  # Use masked PAN
        })
        
        state["credit_data"] = result
        
        # Check minimum credit score
        if result.get("credit_score", 0) < 700:
            state["is_eligible"] = False
            state["rejection_reason"] = f"Credit score {result.get('credit_score')} below minimum requirement"
            state["stage"] = "rejected"
        else:
            state["stage"] = "check_policy"
        
        # LLM explanation
        system_prompt = PROMPTS["explain_credit"]
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Credit report: Score {result.get('credit_score')}, Active loans: {result.get('active_loans')}")
        ]
        response = llm.invoke(messages)
        
        state["messages"].append({
            "role": "assistant",
            "content": response.content
        })
        
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
            "age": app_data["age"],
            "credit_score": credit_data["credit_score"],
            "monthly_income": app_data["monthly_income"],
            "employment_type": app_data["employment_type"],
            "requested_amount": app_data["requested_amount"],
            "tenure_months": app_data["tenure_months"],
            "existing_emi": credit_data["existing_emi"],
            "active_loans": credit_data["active_loans"],
            "dpd_30_days": credit_data["dpd_30_days"]
        })
        
        state["policy_validation"] = result
        
        if result["is_eligible"]:
            state["stage"] = "assess_affordability"
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
            
            # LLM explanation
            system_prompt = PROMPTS["explain_affordability"]
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Affordability result: {result}")
            ]
            response = llm.invoke(messages)
            
            state["messages"].append({
                "role": "assistant",
                "content": response.content
            })
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
            "employment_type": app_data["employment_type"],
            "employment_years": app_data["employment_years"],
            "city_tier": app_data["city_tier"],
            "existing_emi": credit_data["existing_emi"],
            "monthly_income": app_data["monthly_income"],
            "active_loans": credit_data["active_loans"],
            "dpd_30_days": credit_data["dpd_30_days"],
            "bureau_flags": credit_data.get("bureau_flags", [])
        })
        
        state["risk_assessment"] = result
        state["stage"] = "generate_offer"
        
        # LLM explanation
        system_prompt = PROMPTS["explain_risk"]
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Risk assessment: {result}")
        ]
        response = llm.invoke(messages)
        
        state["messages"].append({
            "role": "assistant",
            "content": response.content
        })
        
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
            "principal": app_data["final_amount"],
            "tenure_months": app_data["tenure_months"],
            "risk_segment": risk_data["risk_segment"],
            "age": app_data["age"],
            "employment_type": app_data["employment_type"],
            "city_tier": app_data["city_tier"]
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
    
    system_prompt = PROMPTS["explain_offer"].format(**offer)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Present the loan offer and help me understand all details.")
    ]
    
    response = llm.invoke(messages)
    
    state["messages"].append({
        "role": "assistant",
        "content": response.content
    })
    
    state["stage"] = "await_acceptance"
    state["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Offer explained to customer")
    return state


def handle_acceptance_node(state: LoanWorkflowState) -> LoanWorkflowState:
    """
    Decision node: Handle customer's acceptance/rejection
    This is typically triggered by user input
    """
    if state["is_accepted"]:
        state["stage"] = "generate_sanction"
        state["loan_id"] = str(uuid.uuid4())
        
        # LLM confirmation
        system_prompt = PROMPTS["acceptance"]
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Customer accepted the offer")
        ]
        response = llm.invoke(messages)
        
        state["messages"].append({
            "role": "assistant",
            "content": response.content
        })
    else:
        state["stage"] = "completed"
        
        # LLM farewell
        system_prompt = PROMPTS["acceptance"]
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Customer declined the offer")
        ]
        response = llm.invoke(messages)
        
        state["messages"].append({
            "role": "assistant",
            "content": response.content
        })
    
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
    system_prompt = PROMPTS["disbursement"].format(
        loan_id=state["loan_id"],
        net_disbursement=state["loan_offer"]["net_disbursement"]
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Proceed with disbursement simulation")
    ]
    
    response = llm.invoke(messages)
    
    state["messages"].append({
        "role": "assistant",
        "content": response.content
    })
    
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
    required_fields = ["aadhaar", "pan", "monthly_income", "requested_amount", "tenure_months"]
    
    if all(field in app_data for field in required_fields):
        logger.info(f"All required fields collected, proceeding to KYC verification")
        return "verify_kyc"
    
    # Otherwise, stop and wait for more user input
    # Don't loop back to collect_info - that will trigger LLM again
    logger.info(f"Missing fields: {[f for f in required_fields if f not in app_data]}, waiting for user input")
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
