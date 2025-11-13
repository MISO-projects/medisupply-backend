from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone, date
import logging
import httpx 
import os
from sqlalchemy import func, Date, cast
import json
import random
import uuid 

from db.database import get_db
from db.visita import Visita
from schemas.visita_schema import CrearRutaVisitaSchema, RutaVisitaItemSchema, VisitaDetalleResponseSchema, ActualizarVisitaSchema
from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class VisitaService:

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
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
                response = await client.post(
                    f"{self.clientes_service_url}/api/clientes/by-ids",
                    json=request_body
                )
            
            if response.status_code == HTTPStatus.OK:
                data_list = response.json()
                if not data_list:
                    logger.warning(f"Intento de crear visita para cliente inexistente: {cliente_id}")
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail=f"Cliente con ID {cliente_id} no encontrado."
                    )
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
        
    async def _get_clientes_batch_data(self, cliente_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Llama al servicio de Clientes para obtener los datos de múltiples clientes
        usando el endpoint /by-ids.
        """
        if not cliente_ids:
            return []
            
        request_body = {"ids": cliente_ids}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.clientes_service_url}/api/clientes/by-ids",
                    json=request_body
                )
            
            if response.status_code == HTTPStatus.OK:
                return response.json() 
            else:
                logger.error(f"Error del servicio de clientes: {response.status_code} - {response.text}")
                return []
        
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de clientes: {e}")
            return []
        
        
    async def get_rutas_por_fecha_y_vendedor(
        self, 
        fecha: date, 
        vendedor_id: uuid.UUID  
    ) -> List[RutaVisitaItemSchema]:
        """
        Obtiene la lista de visitas programadas para un VENDEDOR 
        en una FECHA específica, enriquecidas con datos del cliente 
        y ordenadas por hora.
        """
        try:
            visitas_db = self.db.query(Visita).filter(
                func.cast(Visita.fecha_visita_programada, Date) == fecha,
                Visita.vendedor_id == vendedor_id 
            ).order_by(
                Visita.fecha_visita_programada.asc()
            ).all()

            if not visitas_db:
                return [] 

            cliente_ids = list(set(str(v.cliente_id) for v in visitas_db))
            
            clientes_data_list = await self._get_clientes_batch_data(cliente_ids)
            clientes_map = {c["id"]: c for c in clientes_data_list}

            resultados = []
            for visita in visitas_db:
                cliente_id_str = str(visita.cliente_id)
                cliente_info = clientes_map.get(cliente_id_str, {})
                hora_formateada = visita.fecha_visita_programada.strftime("%H:%M")
                
                item = RutaVisitaItemSchema(
                    id=visita.id,
                    cliente_id=visita.cliente_id,
                    nombre=cliente_info.get("nombre", "Cliente no encontrado"),
                    direccion=cliente_info.get("address", "Dirección no disponible"),
                    hora_de_la_cita=hora_formateada,
                    estado=visita.estado
                )
                resultados.append(item)

            return resultados

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al obtener rutas por fecha y vendedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener las rutas de visita."
            )
        
    async def get_visita_detalle_por_id(self, visita_id: uuid.UUID) -> VisitaDetalleResponseSchema:
        """
        Obtiene todos los detalles de una visita específica,
        enriquecidos con datos del cliente (nombre, dirección).
        """
        try:
            visita_db = self.db.query(Visita).filter(
                Visita.id == visita_id
            ).first()

            if not visita_db:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Visita con ID {visita_id} no encontrada."
                )

            cliente_id_str = str(visita_db.cliente_id)
            try:
                cliente_data = await self._get_cliente_data(cliente_id_str)
                nombre_cliente = cliente_data.get("nombre", "Cliente no encontrado")
                direccion_cliente = cliente_data.get("address", "Dirección no disponible")
            except HTTPException:
                nombre_cliente = "Cliente no disponible"
                direccion_cliente = "Dirección no disponible"

            visita_dict = visita_db.to_dict()

            visita_dict["nombre_institucion"] = nombre_cliente
            visita_dict["direccion"] = direccion_cliente

            return VisitaDetalleResponseSchema(**visita_dict)

        except HTTPException as he:
            raise he
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al obtener detalle de visita {visita_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener el detalle de la visita."
            )
        
    async def actualizar_visita(
        self, 
        visita_id: uuid.UUID, 
        data: ActualizarVisitaSchema
    ) -> VisitaDetalleResponseSchema:
        """
        Actualiza campos específicos de una visita existente.
        Aplica validación de transiciones de estado.
        """
        try:
            visita_db = self.db.query(Visita).filter(
                Visita.id == visita_id
            ).first()

            if not visita_db:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Visita con ID {visita_id} no encontrada."
                )

            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="No se proporcionaron datos para actualizar."
                )

            nuevo_estado = update_data.get("estado")
            
            if nuevo_estado:
                estado_actual = visita_db.estado
                
                if estado_actual in ("REALIZADA", "CANCELADA"):
                    
                    if nuevo_estado != estado_actual:
                        logger.warning(
                            f"Intento bloqueado: Cambiar visita {visita_id} de '{estado_actual}' a '{nuevo_estado}'."
                        )
                        raise HTTPException(
                            status_code=HTTPStatus.BAD_REQUEST,
                            detail=f"No se puede cambiar el estado de una visita que ya está '{estado_actual}'."
                        )
                

            for key, value in update_data.items():
                setattr(visita_db, key, value)
            
            self.db.add(visita_db)
            self.db.commit()
            self.db.refresh(visita_db)

            logger.info(f"Visita {visita_id} actualizada. Campos: {list(update_data.keys())}")
            return await self.get_visita_detalle_por_id(visita_id)

        except HTTPException as he:
            self.db.rollback()
            raise he
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar visita {visita_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar la visita."
            )

def get_visita_service(db: Session = Depends(get_db)) -> VisitaService:
    return VisitaService(db)