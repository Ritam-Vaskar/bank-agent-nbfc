"""
Main FastAPI application entry point
NBFC Digital Lending Platform Backend
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from config import settings
from database import mongodb, redis_client
from middleware.audit_logger import audit_middleware
import os

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=logging.INFO if settings.is_development else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Set console handler encoding to UTF-8 for emoji support on Windows
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.stream.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application
    Handles startup and shutdown events
    """
    # Startup
    logger.info("=" * 70)
    logger.info("🚀 Starting NBFC Loan Platform Backend...")
    logger.info("=" * 70)
    
    # Connect to MongoDB
    try:
        await mongodb.connect()
        logger.info("✅ MongoDB connected successfully")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise
    
    # Load mock bureau data
    try:
        from engines.bureau_engine import bureau_engine
        bureau_engine.load_mock_dataset()
        logger.info("✅ Bureau mock data loaded (using fallback generation)")
    except Exception as e:
        logger.warning(f"⚠️  Could not load bureau data: {str(e)} (will generate on-the-fly)")
    
    logger.info("=" * 70)
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Backend URL: {settings.BACKEND_URL}")
    logger.info(f"🎨 Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"📚 API Docs: {settings.BACKEND_URL}/docs")
    logger.info("=" * 70)
    logger.info("✨ All systems operational - Ready to process loan applications!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down NBFC Loan Platform Backend...")
    await mongodb.disconnect()
    await redis_client.disconnect()
    logger.info("👋 Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="NBFC Digital Lending Platform API",
    description="Production-grade digital lending platform with LangGraph orchestration",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan
)

# Audit logging middleware
app.middleware("http")(audit_middleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for container orchestration"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {
            "mongodb": "connected" if mongodb.is_connected else "disconnected",
            "redis": "connected" if redis_client.is_connected else "disconnected"
        }
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "message": "NBFC Digital Lending Platform API",
        "version": "1.0.0",
        "docs": "/docs" if settings.is_development else "Documentation disabled in production",
        "health": "/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
logger.info("📦 Loading API routers...")

from routes.auth import router as auth_router
from routes.loans import router as loans_router
from routes.admin import router as admin_router

app.include_router(auth_router, prefix="/api")
app.include_router(loans_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

logger.info("✅ All routers loaded successfully")
logger.info("   - /api/auth (Authentication)")
logger.info("   - /api/loans (Loan Applications & Workflow)")
logger.info("   - /api/admin (Admin & Analytics)")
# app.include_router(loans.router, prefix="/loans", tags=["Loans"])
# app.include_router(kyc.router, prefix="/kyc", tags=["KYC"])
# app.include_router(admin.router, prefix="/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development
    )
