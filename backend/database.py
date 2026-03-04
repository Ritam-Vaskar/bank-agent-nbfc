"""
Database connection and client management
Handles MongoDB and Redis connections
"""

import motor.motor_asyncio
import redis.asyncio as aioredis
from typing import Optional
import logging

from config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        self._is_connected = False
    
    async def connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            self._is_connected = True
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("MongoDB connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self._is_connected
    
    # Collection shortcuts
    @property
    def users(self):
        """Users collection"""
        return self.db.users if self.db else None
    
    @property
    def loan_applications(self):
        """Loan applications collection"""
        return self.db.loan_applications if self.db else None
    
    @property
    def loans(self):
        """Loans collection"""
        return self.db.loans if self.db else None
    
    @property
    def audit_logs(self):
        """Audit logs collection"""
        return self.db.audit_logs if self.db else None
    
    @property
    def consent_records(self):
        """Consent records collection"""
        return self.db.consent_records if self.db else None


class RedisClient:
    """Redis connection manager"""
    
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self._is_connected = False
    
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            self._is_connected = True
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self._is_connected = False
            logger.info("Redis connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._is_connected
    
    # OTP operations
    async def set_otp(self, email: str, hashed_otp: str, expiry_seconds: int = 300):
        """Store OTP in Redis"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"otp:{email}"
        data = {
            "hashed_otp": hashed_otp,
            "attempts": "0"
        }
        await self.client.hset(key, mapping=data)
        await self.client.expire(key, expiry_seconds)
        logger.info(f"OTP set for {email} with expiry {expiry_seconds}s")
    
    async def get_otp(self, email: str) -> Optional[dict]:
        """Retrieve OTP from Redis"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"otp:{email}"
        data = await self.client.hgetall(key)
        return data if data else None
    
    async def increment_otp_attempts(self, email: str):
        """Increment OTP verification attempts"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"otp:{email}"
        await self.client.hincrby(key, "attempts", 1)
    
    async def delete_otp(self, email: str):
        """Delete OTP from Redis"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"otp:{email}"
        await self.client.delete(key)
        logger.info(f"OTP deleted for {email}")
    
    # JWT blacklist operations
    async def blacklist_token(self, token_id: str, expiry_seconds: int = 86400):
        """Add token to blacklist"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"jwt_blacklist:{token_id}"
        await self.client.set(key, "1", ex=expiry_seconds)
        logger.info(f"Token {token_id} blacklisted")
    
    async def is_token_blacklisted(self, token_id: str) -> bool:
        """Check if token is blacklisted"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"jwt_blacklist:{token_id}"
        result = await self.client.exists(key)
        return result > 0
    
    # Cache operations
    async def cache_bureau_data(self, pan: str, data: dict, ttl_seconds: int = 86400):
        """Cache credit bureau data"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"bureau_cache:{pan}"
        await self.client.setex(key, ttl_seconds, str(data))
        logger.info(f"Bureau data cached for PAN ending {pan[-4:]}")
    
    async def get_cached_bureau_data(self, pan: str) -> Optional[str]:
        """Retrieve cached bureau data"""
        if not self.client:
            raise Exception("Redis client not connected")
        
        key = f"bureau_cache:{pan}"
        return await self.client.get(key)


# Global instances
mongodb = MongoDB()
redis_client = RedisClient()
