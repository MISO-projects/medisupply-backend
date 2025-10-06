from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Depends
from db.database import get_db


class HealthService:
    """Simple service class for checking database and cache health"""

    def __init__(
        self,
        db: Session = Depends(get_db),
    ):
        self.db = db

    def check_database_health(self) -> Dict[str, Any]:
        """Check if database is accessible"""
        try:
            self.db.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "database"}
        except Exception as e:
            return {"status": "unhealthy", "service": "database", "error": str(e)}

    def check_overall_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        db_health = self.check_database_health()

        overall_healthy = db_health["status"] == "healthy"

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "database": db_health,
        }


def get_health_service(
    db: Session = Depends(get_db),
) -> HealthService:
    """Dependency function to get health service instance"""
    return HealthService(db=db)
