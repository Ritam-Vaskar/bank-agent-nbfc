"""
Audit log model for compliance and tracking
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4


class AuditLog(BaseModel):
    """Audit log document for compliance tracking"""
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Entity tracking
    user_id: Optional[str] = None
    application_id: Optional[str] = None
    loan_id: Optional[str] = None
    
    # Action details
    action: str  # E.g., "KYC_VERIFICATION", "RISK_ASSESSMENT", "LOAN_APPROVAL"
    decision: Optional[Literal["APPROVED", "REJECTED", "PENDING", "INFO"]] = "INFO"
    actor: Optional[str] = None  # System, Admin, User
    
    # Technical details
    risk_score: Optional[float] = None
    policy_version: Optional[str] = None
    workflow_stage: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Message and details
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "log_id": "log-123e4567",
                "user_id": "user-123e4567",
                "application_id": "app-123e4567",
                "action": "RISK_ASSESSMENT",
                "decision": "APPROVED",
                "risk_score": 0.25,
                "policy_version": "1.0.0",
                "message": "Risk assessment completed - LOW risk segment",
"timestamp": "2026-03-05T10:00:00"
            }
        }


class AuditLogCreate(BaseModel):
    """Schema for creating audit log"""
    user_id: Optional[str] = None
    application_id: Optional[str] = None
    loan_id: Optional[str] = None
    action: str
    decision: Optional[Literal["APPROVED", "REJECTED", "PENDING", "INFO"]] = "INFO"
    risk_score: Optional[float] = None
    policy_version: Optional[str] = None
    workflow_stage: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseModel):
    """Schema for audit log API responses"""
    log_id: str
    action: str
    decision: Optional[str]
    message: Optional[str]
    timestamp: datetime
