"""
Admin Routes
Analytics, monitoring, and administrative functions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from auth.dependencies import get_current_user, require_role
from models.user import User
from database import mongodb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/applications")
async def list_all_applications(
    status_filter: Optional[str] = None,
    loan_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role("admin"))
):
    """
    List all loan applications (admin only)
    
    Args:
        status_filter: Filter by status
        loan_type: Filter by loan type
        limit: Maximum results
        current_user: Admin user
    
    Returns:
        List of all applications with filters
    """
    try:
        query = {}
        if status_filter:
            query["status"] = status_filter.upper()
        if loan_type:
            query["loan_type"] = loan_type
        
        cursor = mongodb.loan_applications.find(query).sort("created_at", -1).limit(limit)
        applications = await cursor.to_list(length=limit)
        
        for app in applications:
            app.pop("_id", None)
            # Mask sensitive data
            if app.get("kyc_data"):
                app["kyc_data"].pop("aadhaar_encrypted", None)
                app["kyc_data"].pop("pan_encrypted", None)
        
        logger.info(f"Admin {current_user.user_id} retrieved {len(applications)} applications")
        
        return {
            "total": len(applications),
            "applications": applications
        }
        
    except Exception as e:
        logger.error(f"Error listing applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applications: {str(e)}"
        )


@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(require_role("admin"))
):
    """
    Get overall platform analytics
    
    Returns:
        Key metrics and statistics
    """
    try:
        # Total applications
        total_apps = await mongodb.loan_applications.count_documents({})
        
        # Applications by status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = await mongodb.loan_applications.aggregate(pipeline).to_list(None)
        status_distribution = {item["_id"]: item["count"] for item in status_counts}
        
        # Total loans disbursed
        total_loans = await mongodb.loans.count_documents({"status": "ACTIVE"})
        
        # Total disbursed amount
        pipeline = [
            {"$match": {"status": "ACTIVE"}},
            {"$group": {"_id": None, "total": {"$sum": "$disbursement_amount"}}}
        ]
        result = await mongodb.loans.aggregate(pipeline).to_list(None)
        total_disbursed = result[0]["total"] if result else 0
        
        # Applications in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_apps = await mongodb.loan_applications.count_documents({
            "created_at": {"$gte": week_ago}
        })
        
        # Approval rate
        approved = status_distribution.get("APPROVED", 0)
        rejected = status_distribution.get("REJECTED", 0)
        declined = status_distribution.get("DECLINED", 0)
        total_decided = approved + rejected + declined
        approval_rate = (approved / total_decided * 100) if total_decided > 0 else 0
        
        logger.info(f"Admin {current_user.user_id} accessed analytics overview")
        
        return {
            "total_applications": total_apps,
            "status_distribution": status_distribution,
            "total_active_loans": total_loans,
            "total_disbursed_amount": total_disbursed,
            "recent_applications_7d": recent_apps,
            "approval_rate": round(approval_rate, 2),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics: {str(e)}"
        )


@router.get("/analytics/risk-distribution")
async def get_risk_distribution(
    current_user: User = Depends(require_role("admin"))
):
    """
    Get distribution of applications by risk segment
    
    Returns:
        Risk segment statistics
    """
    try:
        pipeline = [
            {"$match": {"risk_assessment": {"$exists": True}}},
            {"$group": {
                "_id": "$risk_assessment.risk_segment",
                "count": {"$sum": 1},
                "avg_risk_score": {"$avg": "$risk_assessment.risk_score"}
            }}
        ]
        
        result = await mongodb.loan_applications.aggregate(pipeline).to_list(None)
        
        risk_distribution = {
            item["_id"]: {
                "count": item["count"],
                "avg_risk_score": round(item["avg_risk_score"], 3)
            }
            for item in result
        }
        
        logger.info(f"Admin {current_user.user_id} accessed risk distribution analytics")
        
        return {
            "risk_distribution": risk_distribution,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating risk distribution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate risk analytics: {str(e)}"
        )


@router.get("/analytics/loan-types")
async def get_loan_type_analytics(
    current_user: User = Depends(require_role("admin"))
):
    """
    Get analytics by loan type
    
    Returns:
        Loan type statistics
    """
    try:
        pipeline = [
            {"$group": {
                "_id": "$loan_type",
                "total_applications": {"$sum": 1},
                "approved": {
                    "$sum": {"$cond": [{"$eq": ["$status", "APPROVED"]}, 1, 0]}
                }
            }}
        ]
        
        result = await mongodb.loan_applications.aggregate(pipeline).to_list(None)
        
        loan_type_stats = {
            item["_id"]: {
                "total_applications": item["total_applications"],
                "approved": item["approved"],
                "approval_rate": round(item["approved"] / item["total_applications"] * 100, 2)
            }
            for item in result
        }
        
        logger.info(f"Admin {current_user.user_id} accessed loan type analytics")
        
        return {
            "loan_type_stats": loan_type_stats,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating loan type analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate loan type analytics: {str(e)}"
        )


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    application_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role("admin"))
):
    """
    Fetch audit logs with filters
    
    Args:
        user_id: Filter by user ID
        application_id: Filter by application ID
        action: Filter by action type
        limit: Maximum results
        current_user: Admin user
    
    Returns:
        Filtered audit logs
    """
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        if application_id:
            query["application_id"] = application_id
        if action:
            query["action"] = action
        
        cursor = mongodb.audit_logs.find(query).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        for log in logs:
            log.pop("_id", None)
        
        logger.info(f"Admin {current_user.user_id} accessed audit logs (retrieved {len(logs)} records)")
        
        return {
            "total": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch audit logs: {str(e)}"
        )


@router.get("/users/{user_id}/applications")
async def get_user_applications(
    user_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """
    Get all applications for a specific user (admin only)
    
    Args:
        user_id: Target user ID
        current_user: Admin user
    
    Returns:
        User's applications
    """
    try:
        cursor = mongodb.loan_applications.find({"user_id": user_id}).sort("created_at", -1)
        applications = await cursor.to_list(length=100)
        
        for app in applications:
            app.pop("_id", None)
            # Mask sensitive data
            if app.get("kyc_data"):
                app["kyc_data"].pop("aadhaar_encrypted", None)
                app["kyc_data"].pop("pan_encrypted", None)
        
        logger.info(f"Admin {current_user.user_id} accessed applications for user {user_id}")
        
        return {
            "user_id": user_id,
            "total_applications": len(applications),
            "applications": applications
        }
        
    except Exception as e:
        logger.error(f"Error fetching user applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user applications: {str(e)}"
        )


@router.get("/health-check")
async def admin_health_check(
    current_user: User = Depends(require_role("admin"))
):
    """
    Comprehensive health check for admin monitoring
    
    Returns:
        System health status
    """
    try:
        # Check MongoDB
        mongo_ok = False
        try:
            await mongodb.client.server_info()
            mongo_ok = True
        except:
            pass
        
        # Check Redis
        redis_ok = False
        try:
            await redis_client.client.ping()
            redis_ok = True
        except:
            pass
        
        # Check collections
        collections = await mongodb.db.list_collection_names()
        
        return {
            "status": "healthy" if (mongo_ok and redis_ok) else "degraded",
            "mongodb": "connected" if mongo_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
            "collections": collections,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
