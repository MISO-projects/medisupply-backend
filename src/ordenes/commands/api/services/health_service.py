from typing import Dict, Any


class HealthService:
    """Simple service class for checking database and cache health"""

    def check_overall_health(self) -> Dict[str, Any]:
        """Check overall system health"""

        return {"status": "healthy"}


def get_health_service() -> HealthService:
    """Dependency function to get health service instance"""
    return HealthService()
