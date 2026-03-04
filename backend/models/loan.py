"""
Loan model for active/disbursed loans
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import uuid4


class EMIInstallment(BaseModel):
    """Individual EMI installment in amortization schedule"""
    month: int
    due_date: datetime
    emi_amount: float
    principal_component: float
    interest_component: float
    remaining_balance: float
    status: Literal["PENDING", "PAID", "OVERDUE"] = "PENDING"
    paid_date: Optional[datetime] = None
    payment_transaction_id: Optional[str] = None


class Loan(BaseModel):
    """Active loan document"""
    loan_id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    user_id: str
    loan_type: str
    
    # Loan terms
    principal: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    processing_fee: float
    total_interest: float
    total_repayment: float
    
    # Status tracking
    status: Literal["ACTIVE", "CLOSED", "DEFAULTED", "FORECLOSED"] = "ACTIVE"
    disbursement_status: Literal["PENDING", "COMPLETED", "FAILED"] = "PENDING"
    
    # Disbursement details
    disbursement_date: Optional[datetime] = None
    disbursement_transaction_id: Optional[str] = None
    disbursement_account_number: Optional[str] = None
    
    # EMI Schedule
    emi_schedule: List[EMIInstallment] = Field(default_factory=list)
    next_due_date: Optional[datetime] = None
    total_paid: float = 0.0
    principal_paid: float = 0.0
    interest_paid: float = 0.0
    outstanding_principal: Optional[float] = None
    
    # Documents
    sanction_letter_url: Optional[str] = None
    agreement_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "loan_id": "loan-123e4567",
                "application_id": "app-123e4567",
                "user_id": "user-123e4567",
                "loan_type": "personal_loan",
                "principal": 500000,
                "tenure_months": 36,
                "interest_rate": 12.5,
                "monthly_emi": 16680,
                "status": "ACTIVE"
            }
        }


class LoanResponse(BaseModel):
    """Schema for loan API responses"""
    loan_id: str
    loan_type: str
    principal: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    status: str
    disbursement_date: Optional[datetime]
    next_due_date: Optional[datetime]
    outstanding_principal: float
    created_at: datetime


class EMIScheduleResponse(BaseModel):
    """Schema for EMI schedule API response"""
    loan_id: str
    total_installments: int
    schedule: List[EMIInstallment]
