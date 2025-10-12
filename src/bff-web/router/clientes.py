from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
import logging

from services.clientes_service import ClientesService, get_clientes_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clientes_router = APIRouter()

@clientes_router.get("/health")
def health_check(clientes_service: ClientesService = Depends(get_clientes_service)):
    return clientes_service.health_check()

@clientes_router.get(
    "/asignados",
    summary="Obtener clientes asignados al vendedor autenticado",
    description="Retorna la lista de clientes institucionales asignados al vendedor autenticado"
)
def get_clientes_asignados(
    clientes_service: ClientesService = Depends(get_clientes_service),
    authorization: str = Header(..., alias="Authorization")
):
    try:
        logger.info("BFF: Solicitud de clientes asignados recibida")
        
        # Reenviar la solicitud al servicio de clientes
        result = clientes_service.get_clientes_asignados(authorization)
        
        logger.info(f"BFF: Retornando {result.get('total', 0)} clientes asignados")
        return result
        
    except HTTPException:
        # Re-lanzar excepciones HTTP del servicio
        raise
    except Exception as e:
        logger.error(f"BFF: Error interno al procesar solicitud de clientes asignados: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF"
        )

@clientes_router.get(
    "/asignados/{cliente_id}",
    summary="Obtener un cliente específico asignado al vendedor",
    description="Retorna un cliente específico si está asignado al vendedor autenticado"
)
def get_cliente_asignado(
    cliente_id: str,
    clientes_service: ClientesService = Depends(get_clientes_service),
    authorization: str = Header(..., alias="Authorization")
):
    try:
        logger.info(f"BFF: Solicitud de cliente {cliente_id} recibida")
        
        # Reenviar la solicitud al servicio de clientes
        result = clientes_service.get_cliente_asignado(cliente_id, authorization)
        
        logger.info(f"BFF: Cliente {cliente_id} encontrado y retornado")
        return result
        
    except HTTPException:
        # Re-lanzar excepciones HTTP del servicio
        raise
    except Exception as e:
        logger.error(f"BFF: Error interno al procesar solicitud de cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF"
        )

