from typing import Dict, Any
import logging
from .autenticacion_service import AutenticacionService
from .clientes_service import ClientesService
from .ordenes_commands_service import OrdenesCommandsService
from .ordenes_queries_service import OrdenesQueriesService

logger = logging.getLogger(__name__)


class HealthService:

    def __init__(self):
        self.services = {
            "autenticacion": AutenticacionService(),
            "clientes": ClientesService(),
            "ordenes_commands": OrdenesCommandsService(),
            "ordenes_queries": OrdenesQueriesService(),
        }

    def check_overall_health(self, include_details: bool = False) -> Dict[str, Any]:
        
        health_status = {
            "status": "healthy",
            "services": {}
        }
        
        for service_name, service_instance in self.services.items():
            try:
                service_health = service_instance.health_check()
                service_status = {"status": "healthy"}
                
                if include_details:
                    service_status["details"] = service_health
                    
                health_status["services"][service_name] = service_status
            except Exception as e:
                logger.error(f"{service_name} service health check failed: {e}")
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        return health_status
    



def get_health_service() -> HealthService:
    """Dependency function to get health service instance"""
    return HealthService()

