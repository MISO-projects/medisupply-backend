from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone, date
import logging
import httpx 
import os
from sqlalchemy import func
import json
import random
import uuid 

from db.database import get_db
from db.visita import Visita
from schemas.visita_schema import CrearRutaVisitaSchema 
from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class VisitaService:

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
        self.productos_service_url = os.getenv(
            "PRODUCTOS_SERVICE_URL", "http://productos-service:3000"
        )
        # Asume el nombre y puerto del servicio de clientes. ¡Ajústalo si es necesario!
        self.clientes_service_url = os.getenv(
            "CLIENTES_SERVICE_URL", "http://clientes-service:3000"
        )
        # ---------------

    async def _get_cliente_data(self, cliente_id: str) -> Dict[str, Any]:
        """
        Llama al servicio de Clientes para obtener los datos de un cliente
        usando el endpoint /by-ids.
        """
        request_body = {"ids": [cliente_id]}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Asumo que la ruta completa es /api/clientes/by-ids
                response = await client.post(
                    f"{self.clientes_service_url}/api/clientes/by-ids",
                    json=request_body
                )
            
            if response.status_code == HTTPStatus.OK:
                data_list = response.json()
                if not data_list:
                    # Validación 1: El cliente no existe
                    logger.warning(f"Intento de crear visita para cliente inexistente: {cliente_id}")
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail=f"Cliente con ID {cliente_id} no encontrado."
                    )
                # Retorna el primer (y único) cliente encontrado
                return data_list[0]
            else:
                logger.error(f"Error del servicio de clientes: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    detail="Error al comunicarse con el servicio de clientes."
                )
        
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de clientes: {e}")
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con el servicio de clientes."
            )


    async def crear_ruta_visita(self, data: CrearRutaVisitaSchema) -> Dict[str, Any]:
        """
        Crea un nuevo registro de visita (ruta).
        1. Valida el cliente_id llamando al servicio de Clientes.
        2. Extrae el vendedor_id de la respuesta del cliente.
        3. Genera una fecha de visita programada aleatoria para hoy.
        """
        
        cliente_data = await self._get_cliente_data(str(data.cliente_id))
        
        vendedor_id_str = cliente_data.get("id_vendedor")
        
        if not vendedor_id_str:
            logger.warning(f"Cliente {data.cliente_id} no tiene vendedor asignado.")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"El cliente {data.cliente_id} no tiene un vendedor asignado."
            )
        
        try:
            vendedor_id_uuid = uuid.UUID(vendedor_id_str)
        except ValueError:
            logger.error(f"El id_vendedor '{vendedor_id_str}' no es un UUID válido.")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="El ID del vendedor recibido del servicio de clientes no es válido."
            )

        try:
            hoy = datetime.now(timezone.utc)
            hora_aleatoria = random.randint(8, 17)
            minuto_aleatorio = random.choice([0, 15, 30, 45])
            
            fecha_programada = hoy.replace(
                hour=hora_aleatoria, 
                minute=minuto_aleatorio, 
                second=0, 
                microsecond=0
            )

            nueva_visita = Visita(
                cliente_id=data.cliente_id,
                vendedor_id=vendedor_id_uuid, 
                fecha_visita_programada=fecha_programada
            )
            
            self.db.add(nueva_visita)
            self.db.commit()
            self.db.refresh(nueva_visita)
            
            logger.info(f"Nueva ruta de visita creada con ID: {nueva_visita.id}")
            return nueva_visita.to_dict()
            
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Integrity error creating visita: {ie}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Error de integridad. Verifique los IDs."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating visita: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al crear la ruta de visita."
            )

def get_visita_service(db: Session = Depends(get_db)) -> VisitaService:
    return VisitaService(db)