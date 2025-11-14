from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
import base64
import json
from http import HTTPStatus

from db.database import get_db
from schemas.schemas import (
    EventoInventarioSchema,
    RegistrarEmailSchema,
    EmailNotificacionResponseSchema,
    ActualizarEmailSchema,
    AlertaResponseSchema,
    AlertasListResponse,
    RevisarAlertaSchema,
    EstadisticasAlertasResponse
)
from services.auditoria_service import AuditoriaService, get_auditoria_service

logger = logging.getLogger(__name__)

auditoria_router = APIRouter()


# ============= ENDPOINTS DE EVENTOS =============

@auditoria_router.post(
    "/eventos/inventario",
    summary="Recibir evento de inventario desde Pub/Sub",
    description="Endpoint que recibe eventos de inventario, los analiza y genera alertas si es necesario"
)
async def recibir_evento_inventario(
    request: Request,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """
    Endpoint que recibe eventos de inventario desde Pub/Sub.
    Analiza el evento y genera alertas si detecta patrones sospechosos.
    """
    try:
        # Extraer el mensaje de Pub/Sub
        envelope = await request.json()
        
        # Decodificar el mensaje
        if "message" in envelope:
            message_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
            evento_dict = json.loads(message_data)
        else:
            evento_dict = envelope
        
        # Validar con schema
        evento = EventoInventarioSchema(**evento_dict)
        
        logger.info(f"Evento de inventario recibido: {evento.operation}")
        
        # Procesar el evento
        resultado = await service.procesar_evento_inventario(evento)
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error procesando evento de inventario: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============= ENDPOINTS DE EMAILS =============

@auditoria_router.post(
    "/emails",
    response_model=EmailNotificacionResponseSchema,
    status_code=HTTPStatus.CREATED,
    summary="Registrar email para notificaciones",
    description="Registra un nuevo email que recibirá alertas de seguridad"
)
def registrar_email(
    email_data: RegistrarEmailSchema,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Registra un nuevo email para recibir notificaciones de alertas"""
    email = service.registrar_email(email_data)
    return email


@auditoria_router.get(
    "/emails",
    response_model=list[EmailNotificacionResponseSchema],
    summary="Listar emails registrados",
    description="Obtiene la lista de emails registrados para notificaciones"
)
def listar_emails(
    activos_solo: bool = Query(False, description="Filtrar solo emails activos"),
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Lista todos los emails registrados"""
    emails = service.listar_emails(activos_solo)
    return emails


@auditoria_router.put(
    "/emails/{email_id}",
    response_model=EmailNotificacionResponseSchema,
    summary="Actualizar configuración de email",
    description="Actualiza la configuración de un email registrado"
)
def actualizar_email(
    email_id: str,
    update_data: ActualizarEmailSchema,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Actualiza la configuración de un email"""
    email = service.actualizar_email(email_id, update_data)
    return email


@auditoria_router.delete(
    "/emails/{email_id}",
    summary="Eliminar email",
    description="Desactiva un email para que no reciba más notificaciones"
)
def eliminar_email(
    email_id: str,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Elimina (desactiva) un email"""
    return service.eliminar_email(email_id)


# ============= ENDPOINTS DE ALERTAS =============

@auditoria_router.get(
    "/alertas",
    response_model=AlertasListResponse,
    summary="Listar alertas",
    description="Obtiene una lista paginada de alertas con filtros opcionales"
)
def listar_alertas(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    severidad: Optional[str] = Query(None, description="Filtrar por severidad (BAJA, MEDIA, ALTA, CRITICA)"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (PENDIENTE, REVISADO, RESUELTO, FALSA_ALARMA)"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de alerta"),
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Lista alertas con filtros y paginación"""
    skip = (page - 1) * page_size
    
    alertas, total = service.listar_alertas(
        skip=skip,
        limit=page_size,
        severidad=severidad,
        estado=estado,
        tipo=tipo
    )
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return AlertasListResponse(
        items=alertas,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@auditoria_router.get(
    "/alertas/{alerta_id}",
    response_model=AlertaResponseSchema,
    summary="Obtener alerta",
    description="Obtiene los detalles de una alerta específica"
)
def obtener_alerta(
    alerta_id: str,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Obtiene una alerta por ID"""
    alerta = service.obtener_alerta(alerta_id)
    return alerta


@auditoria_router.put(
    "/alertas/{alerta_id}/revisar",
    response_model=AlertaResponseSchema,
    summary="Revisar alerta",
    description="Marca una alerta como revisada, resuelta o falsa alarma"
)
def revisar_alerta(
    alerta_id: str,
    revision_data: RevisarAlertaSchema,
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Marca una alerta como revisada/resuelta"""
    alerta = service.revisar_alerta(alerta_id, revision_data)
    return alerta


@auditoria_router.get(
    "/alertas/estadisticas/resumen",
    response_model=EstadisticasAlertasResponse,
    summary="Estadísticas de alertas",
    description="Obtiene estadísticas generales de las alertas del sistema"
)
def obtener_estadisticas_alertas(
    service: AuditoriaService = Depends(get_auditoria_service)
):
    """Obtiene estadísticas generales de alertas"""
    return service.obtener_estadisticas_alertas()






