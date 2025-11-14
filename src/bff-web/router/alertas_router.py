from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
import logging
from http import HTTPStatus

from services.alertas_service import AlertasService, get_alertas_service
from schemas.alertas_schema import (
    AlertasListResponse,
    AlertaDetalleResponse,
    RevisarAlertaRequest,
    EstadisticasAlertasResponse,
    EmailNotificacionResponse,
    RegistrarEmailRequest
)

logger = logging.getLogger(__name__)

alertas_router = APIRouter(prefix="/alertas", tags=["Alertas de Seguridad"])


@alertas_router.get(
    "/",
    response_model=AlertasListResponse,
    summary="Listar alertas de seguridad",
    description="Obtiene una lista paginada de alertas con filtros opcionales"
)
async def listar_alertas(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    severidad: Optional[str] = Query(None, description="Filtrar por severidad (BAJA, MEDIA, ALTA, CRITICA)"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (PENDIENTE, REVISADO, RESUELTO, FALSA_ALARMA)"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de alerta"),
    service: AlertasService = Depends(get_alertas_service)
):
    """
    Lista todas las alertas del sistema con filtros y paginación.
    Usado por el dashboard de administración.
    """
    try:
        resultado = await service.listar_alertas(
            page=page,
            page_size=page_size,
            severidad=severidad,
            estado=estado,
            tipo=tipo
        )
        return resultado
    except Exception as e:
        logger.error(f"Error listando alertas: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al obtener las alertas"
        )


@alertas_router.get(
    "/{alerta_id}",
    response_model=AlertaDetalleResponse,
    summary="Obtener detalle de alerta",
    description="Obtiene los detalles completos de una alerta específica"
)
async def obtener_alerta(
    alerta_id: str,
    service: AlertasService = Depends(get_alertas_service)
):
    """Obtiene el detalle completo de una alerta"""
    try:
        alerta = await service.obtener_alerta(alerta_id)
        return alerta
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo alerta: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al obtener la alerta"
        )


@alertas_router.put(
    "/{alerta_id}/revisar",
    response_model=AlertaDetalleResponse,
    summary="Revisar alerta",
    description="Marca una alerta como revisada, resuelta o falsa alarma"
)
async def revisar_alerta(
    alerta_id: str,
    revision_data: RevisarAlertaRequest,
    service: AlertasService = Depends(get_alertas_service)
):
    """Actualiza el estado de una alerta después de revisión"""
    try:
        alerta = await service.revisar_alerta(alerta_id, revision_data)
        return alerta
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revisando alerta: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al revisar la alerta"
        )


@alertas_router.get(
    "/estadisticas/resumen",
    response_model=EstadisticasAlertasResponse,
    summary="Estadísticas de alertas",
    description="Obtiene estadísticas generales del sistema de alertas"
)
async def obtener_estadisticas(
    service: AlertasService = Depends(get_alertas_service)
):
    """Obtiene estadísticas para el dashboard"""
    try:
        estadisticas = await service.obtener_estadisticas()
        return estadisticas
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )


# ============= ENDPOINTS DE GESTIÓN DE EMAILS =============

@alertas_router.post(
    "/emails",
    response_model=EmailNotificacionResponse,
    status_code=HTTPStatus.CREATED,
    summary="Registrar email para notificaciones",
    description="Registra un email que recibirá notificaciones de alertas"
)
async def registrar_email(
    email_data: RegistrarEmailRequest,
    service: AlertasService = Depends(get_alertas_service)
):
    """Registra un nuevo email para recibir alertas"""
    try:
        email = await service.registrar_email(email_data)
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registrando email: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al registrar el email"
        )


@alertas_router.get(
    "/emails",
    response_model=list[EmailNotificacionResponse],
    summary="Listar emails registrados",
    description="Obtiene la lista de emails configurados para recibir alertas"
)
async def listar_emails(
    activos_solo: bool = Query(False, description="Filtrar solo emails activos"),
    service: AlertasService = Depends(get_alertas_service)
):
    """Lista todos los emails registrados"""
    try:
        emails = await service.listar_emails(activos_solo)
        return emails
    except Exception as e:
        logger.error(f"Error listando emails: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al listar emails"
        )


@alertas_router.delete(
    "/emails/{email_id}",
    summary="Eliminar email",
    description="Desactiva un email para que no reciba más notificaciones"
)
async def eliminar_email(
    email_id: str,
    service: AlertasService = Depends(get_alertas_service)
):
    """Elimina (desactiva) un email"""
    try:
        resultado = await service.eliminar_email(email_id)
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando email: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el email"
        )






