from typing import Dict, Any, Optional
import httpx
import logging
import os
from http import HTTPStatus
from fastapi import HTTPException

from schemas.alertas_schema import (
    AlertasListResponse,
    AlertaDetalleResponse,
    RevisarAlertaRequest,
    EstadisticasAlertasResponse,
    EmailNotificacionResponse,
    RegistrarEmailRequest
)

logger = logging.getLogger(__name__)


class AlertasService:
    """Servicio BFF para gestión de alertas (se comunica con auditoría-service)"""
    
    def __init__(self):
        self.auditoria_service_url = os.getenv(
            "AUDITORIA_SERVICE_URL",
            "http://auditoria-service:3000"
        )
        self.timeout = 30.0
    
    async def listar_alertas(
        self,
        page: int = 1,
        page_size: int = 20,
        severidad: Optional[str] = None,
        estado: Optional[str] = None,
        tipo: Optional[str] = None
    ) -> AlertasListResponse:
        """Lista alertas desde el servicio de auditoría"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            if severidad:
                params["severidad"] = severidad
            if estado:
                params["estado"] = estado
            if tipo:
                params["tipo"] = tipo
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auditoria_service_url}/api/auditoria/alertas",
                    params=params
                )
                
                if response.status_code == 200:
                    return AlertasListResponse(**response.json())
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al obtener alertas desde el servicio de auditoría"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión con auditoría-service: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listando alertas: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar alertas"
            )
    
    async def obtener_alerta(self, alerta_id: str) -> AlertaDetalleResponse:
        """Obtiene una alerta por ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auditoria_service_url}/api/auditoria/alertas/{alerta_id}"
                )
                
                if response.status_code == 200:
                    return AlertaDetalleResponse(**response.json())
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail="Alerta no encontrada"
                    )
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al obtener la alerta"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo alerta: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener la alerta"
            )
    
    async def revisar_alerta(
        self,
        alerta_id: str,
        revision_data: RevisarAlertaRequest
    ) -> AlertaDetalleResponse:
        """Actualiza el estado de una alerta"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.auditoria_service_url}/api/auditoria/alertas/{alerta_id}/revisar",
                    json=revision_data.dict(exclude_none=True)
                )
                
                if response.status_code == 200:
                    return AlertaDetalleResponse(**response.json())
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail="Alerta no encontrada"
                    )
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al revisar la alerta"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error revisando alerta: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al revisar la alerta"
            )
    
    async def obtener_estadisticas(self) -> EstadisticasAlertasResponse:
        """Obtiene estadísticas de alertas"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auditoria_service_url}/api/auditoria/alertas/estadisticas/resumen"
                )
                
                if response.status_code == 200:
                    return EstadisticasAlertasResponse(**response.json())
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al obtener estadísticas"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener estadísticas"
            )
    
    # ============= Gestión de Emails =============
    
    async def registrar_email(self, email_data: RegistrarEmailRequest) -> EmailNotificacionResponse:
        """Registra un email para notificaciones"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.auditoria_service_url}/api/auditoria/emails",
                    json=email_data.dict(exclude_none=True)
                )
                
                if response.status_code == 201:
                    return EmailNotificacionResponse(**response.json())
                elif response.status_code == 409:
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail="El email ya está registrado"
                    )
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al registrar el email"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registrando email: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al registrar el email"
            )
    
    async def listar_emails(self, activos_solo: bool = False) -> list[EmailNotificacionResponse]:
        """Lista emails registrados"""
        try:
            params = {"activos_solo": activos_solo}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auditoria_service_url}/api/auditoria/emails",
                    params=params
                )
                
                if response.status_code == 200:
                    return [EmailNotificacionResponse(**item) for item in response.json()]
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al listar emails"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listando emails: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar emails"
            )
    
    async def eliminar_email(self, email_id: str) -> Dict[str, str]:
        """Elimina (desactiva) un email"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.auditoria_service_url}/api/auditoria/emails/{email_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail="Email no encontrado"
                    )
                else:
                    logger.error(f"Error desde auditoría-service: {response.status_code}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error al eliminar el email"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de auditoría"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error eliminando email: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al eliminar el email"
            )


def get_alertas_service() -> AlertasService:
    """Función de dependencia para obtener instancia del servicio"""
    return AlertasService()






