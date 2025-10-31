from fastapi import APIRouter, Depends, Query, Header, HTTPException, Request
from typing import Optional
from datetime import datetime
import logging
import json
import base64
from services.order_service import OrderService, get_order_service
from schemas.order_schema import (
    PaginatedOrders,
    PaginatedClientOrders,
    SingleOrderResponse,
    IdsResponse,
    CacheHealthResponse,
    CacheInvalidationResponse,
)
import jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

order_router = APIRouter()


def get_client_id_from_auth(authorization: Optional[str] = Header(None)) -> str:

    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autorización requerido")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Formato de token inválido. Debe ser 'Bearer <token>'",
        )

    try:
        token = authorization[7:].strip()

        payload = jwt.decode(token, options={"verify_signature": False})

        role = payload.get("role")
        if role != "client":
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. Solo usuarios con rol 'client' pueden acceder a este recurso",
            )

        id_client = payload.get("id_client")

        if not id_client:
            raise HTTPException(status_code=401, detail="Token no contiene id_client")

        return id_client

    except jwt.DecodeError as e:
        logger.error(f"Error al decodificar token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token mal formado o inválido")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al procesar token de autorización: {str(e)}")
        raise HTTPException(
            status_code=401, detail="Error al procesar token de autorización"
        )


@order_router.get("/", response_model=PaginatedOrders)
async def list_orders(
    estado: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    fecha_creacion_desde: Optional[datetime] = Query(
        None, description="Fecha de creación desde (ISO format)"
    ),
    fecha_creacion_hasta: Optional[datetime] = Query(
        None, description="Fecha de creación hasta (ISO format)"
    ),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        20, ge=1, le=100, description="Tamaño de página (máximo 100)"
    ),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Lista todas las órdenes con opciones de:

    - **Filtros**: Por estado y rango de fecha de creación
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    """
    skip = (page - 1) * page_size

    orders = order_service.list_orders(
        estado=estado,
        fecha_creacion_desde=fecha_creacion_desde,
        fecha_creacion_hasta=fecha_creacion_hasta,
        skip=skip,
        limit=page_size,
    )

    total = order_service.count_orders(
        estado=estado,
        fecha_creacion_desde=fecha_creacion_desde,
        fecha_creacion_hasta=fecha_creacion_hasta,
    )

    return {
        "data": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@order_router.get("/ids", response_model=IdsResponse)
async def get_all_order_ids(order_service: OrderService = Depends(get_order_service)):
    data = order_service.get_all_order_ids()
    return {"data": data}


@order_router.get("/client-orders", response_model=PaginatedClientOrders)
async def get_orders_by_client(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        20, ge=1, le=100, description="Tamaño de página (máximo 100)"
    ),
    client_id: str = Depends(get_client_id_from_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Lista todas las órdenes del cliente autenticado con:
    
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    - **Autenticación**: Requiere token JWT con rol 'client'
    """
    skip = (page - 1) * page_size
    
    orders = order_service.get_orders_by_client(
        id_cliente=client_id,
        skip=skip,
        limit=page_size
    )
    
    total = order_service.count_orders_by_client(client_id)
    
    return {
        "data": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@order_router.get("/{order_id}", response_model=SingleOrderResponse)
async def get_order(order_id: str, order_service: OrderService = Depends(get_order_service)):
    data = order_service.get_order(order_id)
    return {"data": data}


@order_router.get("/health/cache", response_model=CacheHealthResponse)
async def get_cache_health(order_service: OrderService = Depends(get_order_service)):
    """Get cache health status and statistics"""
    return order_service.get_cache_health()


@order_router.post("/cache-invalidation", response_model=CacheInvalidationResponse)
async def handle_cache_invalidation(
    request: Request,
    order_service: OrderService = Depends(get_order_service)
):
    """
    Pub/Sub push endpoint for cache invalidation when order projections are created/updated.
    
    This endpoint is called by Google Cloud Pub/Sub (or the emulator) when a message
    is published to the 'order-projection-created' topic.
    """
    try:
        body = await request.json()
        
        message = body.get("message", {})
        
        if not message:
            logger.warning("Received Pub/Sub message without 'message' field")
            return {"status": "ignored", "reason": "no message field"}
        
        data = message.get("data", "")
        if data:
            decoded_data = base64.b64decode(data).decode("utf-8")
            event_data = json.loads(decoded_data)
        else:
            logger.warning("Received Pub/Sub message without data")
            return {"status": "ignored", "reason": "no data"}
        
        order_id = event_data.get("order_id")
        client_id = event_data.get("client_id")
        event_type = event_data.get("event_type")
        
        logger.info(f"Received cache invalidation event: {event_type} for order {order_id}, client {client_id}")
        
        invalidated = []
        
        if order_id:
            if order_service.invalidate_order_cache(order_id):
                invalidated.append(f"order:{order_id}")
                logger.info(f"Invalidated cache for order {order_id}")
        
        if client_id:
            if order_service.invalidate_client_orders_cache(client_id):
                invalidated.append(f"client_orders:{client_id}")
                logger.info(f"Invalidated all cached orders for client {client_id}")
        
        return {
            "status": "success",
            "invalidated": invalidated,
            "event_type": event_type,
            "order_id": order_id,
            "client_id": client_id
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode Pub/Sub message: {str(e)}")
        return {"status": "error", "reason": "invalid json"}
    except Exception as e:
        logger.error(f"Error handling cache invalidation: {str(e)}")
        # Return 200 to acknowledge the message (cache invalidation is not critical)
        return {"status": "error", "reason": str(e)}
