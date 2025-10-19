from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from schemas.cliente_schema import ClientResponse, RegisterRequest
from db.database import get_db
from db.redis_client import RedisClient
from services.cliente_service import ClienteService
from schemas.cliente_schema import ClienteAsignadoListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


def get_cliente_service(
    db: Session = Depends(get_db),
    redis_client: RedisClient = Depends(lambda: RedisClient())
) -> ClienteService:
    return ClienteService(db=db, redis_client=redis_client)

@router.get(
    "/",
    response_model=List[ClientResponse],
    summary="Obtener lista de clientes",
    description="Retorna la lista de todos los clientes creados"
)
def get_clientes(
    db: Session = Depends(get_db),
    client_service: ClienteService = Depends(get_cliente_service)
):
    return client_service.get_all_clients(db)

# ... (el resto del código del archivo cliente_router.py)

def get_vendedor_id_from_auth(authorization: Optional[str] = Header(None)) -> str:

    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Token de autorización requerido"
        )
    
    # TODO: Implementar validación real del JWT

    try:
        token = authorization.replace("Bearer ", "")
        
        vendedor_id = token
        
        if not vendedor_id:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado"
            )
            
        return vendedor_id
        
    except Exception as e:
        logger.error(f"Error al procesar token de autorización: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Token de autorización inválido"
        )


@router.get(
    "/asignados",
    response_model=ClienteAsignadoListResponse,
    summary="Obtener clientes asignados al vendedor autenticado",
    description="Retorna la lista de clientes institucionales asignados al vendedor autenticado"
)
async def get_clientes_asignados(
    cliente_service: ClienteService = Depends(get_cliente_service),
    vendedor_id: str = Depends(get_vendedor_id_from_auth)
):

    try:
        logger.info(f"Solicitando clientes asignados para vendedor: {vendedor_id}")
        
        clientes_response = cliente_service.get_clientes_asignados(vendedor_id)
        
        logger.info(f"Retornando {clientes_response.total} clientes para vendedor {vendedor_id}")
        return clientes_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno al obtener clientes asignados: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al obtener clientes asignados"
        )


@router.get(
    "/asignados/{cliente_id}",
    summary="Obtener un cliente específico asignado al vendedor",
    description="Retorna un cliente específico si está asignado al vendedor autenticado"
)
async def get_cliente_asignado(
    cliente_id: str,
    cliente_service: ClienteService = Depends(get_cliente_service),
    vendedor_id: str = Depends(get_vendedor_id_from_auth)
):

    try:
        logger.info(f"Solicitando cliente {cliente_id} para vendedor: {vendedor_id}")
        
        cliente = cliente_service.get_cliente_by_id(cliente_id, vendedor_id)
        
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail=f"Cliente {cliente_id} no encontrado o no asignado al vendedor"
            )
        
        logger.info(f"Cliente {cliente_id} encontrado para vendedor {vendedor_id}")
        return cliente
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno al obtener cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al obtener cliente"
        )

@router.post(
    "/",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo cliente institucional",
    description="Registra un nuevo cliente institucional en el sistema"
)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db),
    client_service: ClienteService = Depends(get_cliente_service)
):
    """
    Endpoint para registrar un nuevo cliente institucional

    Args:
        register_data: Datos de registro del cliente institucional
        db: Sesión de base de datos (inyectada)
        client_service: Servicio de clientes (inyectado)

    Returns:
        ClientResponse: Información del cliente institucional creado

    Raises:
        HTTPException 400: Si el cliente ya está registrado
    """

    return client_service.register_client(db, register_data)
