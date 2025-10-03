from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Depends
from db.database import get_db
from db.redis_client import RedisClient, redis_client


class HealthService:
    """Simple service class for checking database and cache health"""
    
    def __init__(
        self,
        db: Session = Depends(get_db),
        redis_client: RedisClient = Depends(lambda: redis_client)
    ):
        self.db = db
        self.redis_client = redis_client
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check if database is accessible"""
        try:
            self.db.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "database"}
        except Exception as e:
            return {
                "status": "unhealthy", 
                "service": "database",
                "error": str(e)
            }
    
    def check_cache_health(self) -> Dict[str, Any]:
        """Check if Redis cache is accessible"""
        try:
            client = self.redis_client.client
            if client and client.ping():
                return {"status": "healthy", "service": "cache"}
            else:
                return {
                    "status": "unhealthy",
                    "service": "cache", 
                    "error": "Redis not accessible"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "cache",
                "error": str(e)
            }
    
    def check_overall_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        db_health = self.check_database_health()
        cache_health = self.check_cache_health()
        
        overall_healthy = (
            db_health["status"] == "healthy" and 
            cache_health["status"] == "healthy"
        )
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "database": db_health,
            "cache": cache_health
        }


def get_health_service(
    db: Session = Depends(get_db),
    redis_client: RedisClient = Depends(lambda: redis_client)
) -> HealthService:
    """Dependency function to get health service instance"""
    return HealthService(db=db, redis_client=redis_client)
