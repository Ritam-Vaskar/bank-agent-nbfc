"""
Loan Application model
Tracks the entire loan application workflow and state
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from uuid import uuid4


class ApplicationData(BaseModel):
    """Data collected during application process"""
    income: Optional[float] = None
    employment_type: Optional[Literal["salaried", "self_employed", "business"]] = None
    employer_name: Optional[str] = None
    years_experience: Optional[int] = None
    requested_amount: Optional[float] = None
    tenure_months: Optional[int] = None
    age: Optional[int] = None
    city_tier: Optional[Literal[1, 2, 3]] = None
    existing_emi: Optional[float] = 0.0
    purpose: Optional[str] = None


class VerificationData(BaseModel):
    """KYC and bureau verification data"""
    kyc_status: Optional[Literal["PENDING", "VERIFIED", "FAILED"]] = "PENDING"
    kyc_verification_id: Optional[str] = None
    encrypted_aadhaar: Optional[str] = None
    encrypted_pan: Optional[str] = None
    credit_score: Optional[int] = None
    credit_report: Optional[Dict[str, Any]] = None
    active_accounts: Optional[int] = None
    total_outstanding: Optional[float] = None
    dpd_30_days: Optional[int] = None
    bureau_flags: Optional[List[str]] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Risk scoring results"""
    risk_score: Optional[float] = None  # 0-1 scale
    risk_segment: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    credit_score_factor: Optional[float] = None
    foir_factor: Optional[float] = None
    employment_stability_factor: Optional[float] = None
    city_tier_factor: Optional[float] = None
    bureau_flags_factor: Optional[float] = None
    explanation: Optional[str] = None


class LoanOffer(BaseModel):
    """Generated loan offer"""
    offered_amount: Optional[float] = None
    tenure_months: Optional[int] = None
    interest_rate: Optional[float] = None
    monthly_emi: Optional[float] = None
    processing_fee: Optional[float] = None
    total_interest: Optional[float] = None
    total_repayment: Optional[float] = None
    offer_valid_until: Optional[datetime] = None


class ConversationMessage(BaseModel):
    """Message in conversation history"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class LoanApplication(BaseModel):
    """Complete loan application document"""
    application_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    loan_type: Literal["personal_loan", "home_loan", "vehicle_loan", "business_loan", "credit_card"]
    status: Literal["PENDING", "IN_PROGRESS", "APPROVED", "REJECTED", "DISBURSED"] = "PENDING"
    workflow_stage: str = "collect_basic_info"
    
    # Application data
    collected_data: ApplicationData = Field(default_factory=ApplicationData)
    verification_data: VerificationData = Field(default_factory=VerificationData)
    risk_assessment: Optional[RiskAssessment] = None
    offer: Optional[LoanOffer] = None
    
    # Workflow tracking
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    policy_version: str = "1.0.0"
    policy_violations: Optional[List[str]] = None
    rejection_reason: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "app-123e4567",
                "user_id": "user-123e4567",
                "loan_type": "personal_loan",
                "status": "IN_PROGRESS",
                "workflow_stage": "verify_kyc",
                "collected_data": {
                    "income": 75000,
                    "employment_type": "salaried",
                    "requested_amount": 500000,
                    "age": 35
                }
            }
        }


class LoanApplicationCreate(BaseModel):
    """Schema for creating new loan application"""
    loan_type: Literal["personal_loan", "home_loan", "vehicle_loan", "business_loan", "credit_card"]


class LoanApplicationResponse(BaseModel):
    """Schema for loan application API responses"""
    application_id: str
    user_id: str
    loan_type: str
    status: str
    workflow_stage: str
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    """Schema for chat message input"""
    message: str
    metadata: Optional[Dict[str, Any]] = None
