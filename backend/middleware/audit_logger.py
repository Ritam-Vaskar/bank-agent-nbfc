"""
Audit Logging Middleware
Logs all critical decisions and actions for compliance
"""

from fastapi import Request
from datetime import datetime
import logging
import uuid
from typing import Dict, Any

from database import mongodb

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logging service for compliance tracking
    - Logs all loan decisions
    - Tracks policy changes
    - Records user actions
    - Ensures RBI compliance
    """
    
    @staticmethod
    async def log(
        action: str,
        user_id: str = None,
        application_id: str = None,
        loan_id: str = None,
        decision: str = None,
        risk_score: float = None,
        policy_version: str = None,
        metadata: Dict[str, Any] = None,
        ip_address: str = None
    ):
        """
        Log an audit event
        
        Args:
            action: Action type (e.g., "KYC_VERIFICATION", "LOAN_APPROVAL")
            user_id: User ID
            application_id: Application ID
            loan_id: Loan ID
            decision: Decision outcome (APPROVED/REJECTED/PENDING)
            risk_score: Risk score if applicable
            policy_version: Policy version used
            metadata: Additional context
            ip_address: Request IP address
        """
        try:
            log_entry = {
                "log_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "user_id": user_id,
                "application_id": application_id,
                "loan_id": loan_id,
                "decision": decision,
                "risk_score": risk_score,
                "policy_version": policy_version or "1.0.0",
                "metadata": metadata or {},
                "ip_address": ip_address
            }
            
            # Insert asynchronously (non-blocking)
            await mongodb.audit_logs.insert_one(log_entry)
            
            logger.info(f"Audit log created: {action} for user {user_id}")
            
        except Exception as e:
            # Never let audit logging crash the main flow
            logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
    
    @staticmethod
    async def log_kyc_verification(
        user_id: str,
        application_id: str,
        success: bool,
        verification_method: str,
        ip_address: str = None
    ):
        """Log KYC verification event"""
        await AuditLogger.log(
            action="KYC_VERIFICATION",
            user_id=user_id,
            application_id=application_id,
            decision="SUCCESS" if success else "FAILED",
            metadata={
                "verification_method": verification_method,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_credit_check(
        user_id: str,
        application_id: str,
        credit_score: int,
        bureau_source: str,
        ip_address: str = None
    ):
        """Log credit bureau check"""
        await AuditLogger.log(
            action="CREDIT_CHECK",
            user_id=user_id,
            application_id=application_id,
            decision="COMPLETED",
            metadata={
                "credit_score": credit_score,
                "bureau_source": bureau_source,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_risk_assessment(
        user_id: str,
        application_id: str,
        risk_score: float,
        risk_segment: str,
        recommendation: str,
        policy_version: str = "1.0.0",
        ip_address: str = None
    ):
        """Log risk assessment"""
        await AuditLogger.log(
            action="RISK_ASSESSMENT",
            user_id=user_id,
            application_id=application_id,
            decision=recommendation,
            risk_score=risk_score,
            policy_version=policy_version,
            metadata={
                "risk_segment": risk_segment,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_loan_decision(
        user_id: str,
        application_id: str,
        decision: str,
        loan_amount: float,
        interest_rate: float,
        risk_score: float = None,
        rejection_reason: str = None,
        policy_version: str = "1.0.0",
        ip_address: str = None
    ):
        """Log final loan approval/rejection decision"""
        await AuditLogger.log(
            action="LOAN_DECISION",
            user_id=user_id,
            application_id=application_id,
            decision=decision,
            risk_score=risk_score,
            policy_version=policy_version,
            metadata={
                "loan_amount": loan_amount,
                "interest_rate": interest_rate,
                "rejection_reason": rejection_reason,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_disbursement(
        user_id: str,
        application_id: str,
        loan_id: str,
        disbursement_amount: float,
        ip_address: str = None
    ):
        """Log loan disbursement"""
        await AuditLogger.log(
            action="LOAN_DISBURSEMENT",
            user_id=user_id,
            application_id=application_id,
            loan_id=loan_id,
            decision="DISBURSED",
            metadata={
                "disbursement_amount": disbursement_amount,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_policy_violation(
        user_id: str,
        application_id: str,
        violations: list,
        policy_version: str = "1.0.0",
        ip_address: str = None
    ):
        """Log policy violations"""
        await AuditLogger.log(
            action="POLICY_VIOLATION",
            user_id=user_id,
            application_id=application_id,
            decision="REJECTED",
            policy_version=policy_version,
            metadata={
                "violations": violations,
                "timestamp": datetime.now().isoformat()
            },
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_user_action(
        action: str,
        user_id: str,
        metadata: Dict[str, Any] = None,
        ip_address: str = None
    ):
        """Log general user action"""
        await AuditLogger.log(
            action=action,
            user_id=user_id,
            decision="COMPLETED",
            metadata=metadata or {},
            ip_address=ip_address
        )


# Middleware function to add audit logging to requests
async def audit_middleware(request: Request, call_next):
    """
    Middleware to automatically log certain request types
    """
    # Get IP address
    ip = request.client.host if request.client else None
    
    # Process request
    response = await call_next(request)
    
    # Log sensitive endpoints (post-request)
    path = request.url.path
    
    # Log authentication events
    if "/auth/verify-otp" in path and response.status_code == 200:
        logger.info(f"User authenticated from IP {ip}")
    
    # Log loan application starts
    if "/loans/apply" in path and response.status_code == 200:
        logger.info(f"Loan application started from IP {ip}")
    
    return response


# Global audit logger instance
audit_logger = AuditLogger()
