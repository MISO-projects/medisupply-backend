from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Optional
import logging

from services.clientes_service import ClientesService, get_clientes_service
from schemas.cliente_schema import ClientResponse, RegisterRequest
from services.clientes_service import get_clientes_service, ClientesService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clientes_router = APIRouter()

@clientes_router.get("/health")
def health_check(clientes_service: ClientesService = Depends(get_clientes_service)):
    return clientes_service.health_check()

@clientes_router.get(
    "/",
    summary="Obtener clientes asignados al vendedor autenticado",
    description="Retorna la lista de clientes institucionales asignados al vendedor autenticado"
)
def get_clientes(
    clientes_service: ClientesService = Depends(get_clientes_service),
    authorization: str = Header(..., alias="Authorization")
):
    try:
        logger.info("BFF Móvil: Solicitud de clientes recibida")
        
        result = clientes_service.get_clientes_asignados(authorization)
        
        logger.info(f"BFF Móvil: Retornando {result.get('total', 0)} clientes asignados")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de clientes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )

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
        logger.info("BFF Móvil: Solicitud de clientes asignados recibida")
        
        result = clientes_service.get_clientes_asignados(authorization)
        
        logger.info(f"BFF Móvil: Retornando {result.get('total', 0)} clientes asignados")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de clientes asignados: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
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
        logger.info(f"BFF Móvil: Solicitud de cliente {cliente_id} recibida")
        
        result = clientes_service.get_cliente_asignado(cliente_id, authorization)
        
        logger.info(f"BFF Móvil: Cliente {cliente_id} encontrado y retornado")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )

@clientes_router.post(
    "/",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo cliente institucional",
    description="Registra un nuevo cliente institucional en el sistema"
)
async def register(
    register_data: RegisterRequest,
    client_service: ClientesService = Depends(get_clientes_service)
):
    """
    Endpoint para registrar un nuevo cliente institucional
    """
    return await client_service.register_client(register_data.model_dump())

