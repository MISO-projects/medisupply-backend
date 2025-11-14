from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone, date, timedelta 
import logging
import httpx 
import os
from sqlalchemy import func, Date, cast, desc
import json
import random
import uuid 

from db.database import get_db
from db.visita import Visita
from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    RutaVisitaItemSchema, 
    VisitaDetalleResponseSchema, 
    ActualizarVisitaSchema,
    VisitaResponseSchema,
    ProductoPreferidoSchema
)
from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class VisitaService:

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
        self.clientes_service_url = os.getenv(
            "CLIENTES_SERVICE_URL", "http://clientes-service:3000"
        )
        self.ordenes_service_url = os.getenv(
            "ORDENES_QUERIES_SERVICE_URL","http://order-query-api:3000"
        )
        # API Key de Google
        self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY") 
        if not self.google_maps_api_key:
            logger.warning("GOOGLE_MAPS_API_KEY no está configurada en las variables de entorno. La optimización de ruta fallará.")

    async def _get_cliente_data(self, cliente_id: str) -> Dict[str, Any]:
        """
        Llama al servicio de Clientes para obtener los datos de un cliente
        usando el endpoint /by-ids.
        """
        request_body = {"ids": [cliente_id]}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{self.clientes_service_url}/api/clientes/by-ids", json=request_body)
            if response.status_code == HTTPStatus.OK:
                data_list = response.json()
                if not data_list:
                    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Cliente con ID {cliente_id} no encontrado.")
                return data_list[0]
            else:
                raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="Error al comunicarse con el servicio de clientes.")
        except httpx.RequestError as e:
            raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="No se pudo conectar con el servicio de clientes.")

    async def _get_top_products_data(self, cliente_id: str) -> List[Dict[str, Any]]:
        """
        Llama al servicio de Órdenes para obtener el Top 5 de productos.
        Usa el endpoint público (pasando client_id como query param).
        """
        endpoint_url = f"{self.ordenes_service_url}/orders/client-top-products"
        params = {"client_id": cliente_id, "limit": 5} 

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint_url, params=params)
            
            if response.status_code == HTTPStatus.OK:
                return response.json().get("data", []) 
            else:
                logger.error(f"Error del servicio de órdenes ({endpoint_url}): {response.status_code} - {response.text}")
                return []
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de órdenes ({endpoint_url}): {e}")
            return []
        
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
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"El cliente {data.cliente_id} no tiene un vendedor asignado.")
        try:
            vendedor_id_uuid = uuid.UUID(vendedor_id_str)
        except ValueError:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="El ID del vendedor recibido del servicio de clientes no es válido.")
        try:
            hoy = datetime.now(timezone.utc)
            dia_semana = hoy.weekday()
            dias_a_sumar = 0
            if dia_semana == 6: dias_a_sumar = 1
            fecha_base = hoy + timedelta(days=dias_a_sumar)
            fecha_programada = fecha_base.replace(hour=0, minute=0, second=0, microsecond=0)
            nueva_visita = Visita(cliente_id=data.cliente_id, vendedor_id=vendedor_id_uuid, fecha_visita_programada=fecha_programada)
            self.db.add(nueva_visita)
            self.db.commit()
            self.db.refresh(nueva_visita)
            logger.info(f"Nueva ruta de visita creada con ID: {nueva_visita.id}")
            return nueva_visita.to_dict()
        except IntegrityError as ie:
            self.db.rollback()
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="Error de integridad. Verifique los IDs.")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Error interno al crear la ruta de visita.")
        
    async def _get_clientes_batch_data(self, cliente_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Llama al servicio de Clientes para obtener los datos de múltiples clientes
        usando el endpoint /by-ids.
        """
        if not cliente_ids: return []
        request_body = {"ids": cliente_ids}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{self.clientes_service_url}/api/clientes/by-ids", json=request_body)
            if response.status_code == HTTPStatus.OK:
                return response.json() 
            else:
                return []
        except httpx.RequestError as e:
            return []
        
        
    # --- FUNCIÓN TOTALMENTE REEMPLAZADA ---
    async def get_rutas_por_fecha_y_vendedor(
        self, 
        fecha: date, 
        vendedor_id: uuid.UUID,
        lat_actual: Optional[float] = None,
        lon_actual: Optional[float] = None
    ) -> List[RutaVisitaItemSchema]:
        """
        Obtiene la lista de todas las visitas del día (Pendientes, Realizadas, Canceladas).
        Si se provee lat/lon, optimiza la ruta de las PENDIENTES y
        devuelve el tiempo de viaje. Las otras se añaden al final.
        """
        try:
            # 1. Obtener visitas PENDIENTES (para optimizar)
            visitas_pendientes_db = self.db.query(Visita).filter(
                func.cast(Visita.fecha_visita_programada, Date) == fecha,
                Visita.vendedor_id == vendedor_id,
                Visita.estado == "PENDIENTE"
            ).all()

            # 2. Obtener visitas REALIZADAS y CANCELADAS (para el final de la lista)
            visitas_otras_db = self.db.query(Visita).filter(
                func.cast(Visita.fecha_visita_programada, Date) == fecha,
                Visita.vendedor_id == vendedor_id,
                Visita.estado.in_(['REALIZADA', 'CANCELADA'])
            ).order_by(Visita.fecha_visita_programada.asc()).all()

            # 3. Obtener datos de clientes (para todas las visitas)
            all_visitas_db = visitas_pendientes_db + visitas_otras_db
            if not all_visitas_db:
                return [] 

            cliente_ids = list(set(str(v.cliente_id) for v in all_visitas_db))
            clientes_data_list = await self._get_clientes_batch_data(cliente_ids)
            clientes_map = {c["id"]: c for c in clientes_data_list}

            # 4. Preparar datos para la lista de PENDIENTES
            visitas_para_procesar = []
            for v in visitas_pendientes_db:
                cliente_info = clientes_map.get(str(v.cliente_id), {})
                visitas_para_procesar.append({
                    "visita_obj": v,
                    "cliente_info": cliente_info
                })

            # 5. Lógica de Optimización (solo para PENDIENTES)
            lista_optimizada_items = []
            
            if lat_actual is not None and lon_actual is not None and self.google_maps_api_key:
                
                origen = f"{lat_actual},{lon_actual}"
                waypoints_coords = []
                visitas_map = {} 
                
                for item in visitas_para_procesar:
                    direccion = item["cliente_info"].get("address", "")
                    coords = direccion.split(",")
                    if len(coords) >= 3 and coords[0] != "NA" and coords[1] != "NA":
                        try:
                            float(coords[0])
                            float(coords[1])
                            coord_str = f"{coords[0]},{coords[1]}"
                            waypoints_coords.append(coord_str)
                            visitas_map[coord_str] = item
                        except ValueError:
                             logger.warning(f"Coordenadas inválidas para visita {item['visita_obj'].id}: {direccion}")
                    
                
                if not waypoints_coords:
                    logger.warning("Ruta del día: Hay visitas pendientes pero ninguna tiene coordenadas válidas.")
                    lista_optimizada_items = visitas_para_procesar 
                
                else:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        params = {
                            "origin": origen,
                            "destination": origen,
                            "waypoints": f"optimize:true|{'|'.join(waypoints_coords)}",
                            "key": self.google_maps_api_key,
                            "units": "metric"
                        }
                        response = await client.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
                    
                    if response.status_code == HTTPStatus.OK:
                        route_data = response.json()
                        if route_data.get("routes") and route_data.get("status") == "OK":
                            route = route_data["routes"][0]
                            waypoint_order = route.get("waypoint_order", []) 
                            legs = route.get("legs", []) 
                            
                            visitas_ordenadas = [visitas_map[waypoints_coords[i]] for i in waypoint_order]
                            
                            if legs:
                                item = visitas_ordenadas[0]
                                item["travel_time"] = legs[0].get("duration", {}).get("text", "N/A")
                                lista_optimizada_items.append(item)
                            
                            for i, leg in enumerate(legs[1:], start=1):
                                if i < len(visitas_ordenadas):
                                    item = visitas_ordenadas[i]
                                    item["travel_time"] = leg.get("duration", {}).get("text", "N/A")
                                    lista_optimizada_items.append(item)
                        else:
                            logger.warning(f"Google Maps no pudo calcular la ruta: {route_data.get('status')}")
                            lista_optimizada_items = visitas_para_procesar
                    else:
                        logger.error(f"Error de Google Maps API: {response.text}")
                        lista_optimizada_items = visitas_para_procesar
            else:
                if not self.google_maps_api_key:
                    logger.warning("No se optimizó la ruta: GOOGLE_MAPS_API_KEY no está configurada.")
                else:
                    logger.info("No se optimizó la ruta: Faltan lat_actual o lon_actual.")
                lista_optimizada_items = visitas_para_procesar

            # 6. Construir la respuesta final
            resultados = []
            
            # 6.1. Añadir las visitas PENDIENTES (optimizadas o no)
            for item in lista_optimizada_items:
                visita = item["visita_obj"]
                cliente_info = item["cliente_info"]
                hora_o_tiempo = item.get("travel_time", "Sin calcular") 
                
                schema_item = RutaVisitaItemSchema(
                    id=visita.id,
                    cliente_id=visita.cliente_id,
                    nombre=cliente_info.get("nombre", "Cliente no encontrado"),
                    direccion=cliente_info.get("address", "Dirección no disponible"),
                    hora_de_la_cita=hora_o_tiempo,
                    estado=visita.estado
                )
                resultados.append(schema_item)

            # 6.2. Añadir las visitas REALIZADAS y CANCELADAS al final
            for visita in visitas_otras_db:
                cliente_info = clientes_map.get(str(visita.cliente_id), {})
                
                schema_item = RutaVisitaItemSchema(
                    id=visita.id,
                    cliente_id=visita.cliente_id,
                    nombre=cliente_info.get("nombre", "Cliente no encontrado"),
                    direccion=cliente_info.get("address", "Dirección no disponible"),
                    hora_de_la_cita="N/A",
                    estado=visita.estado
                )
                resultados.append(schema_item)
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
        enriquecidos con datos del cliente (nombre, dirección) Y
        las notas de visitas anteriores.
        """
        try:
            visita_db = self.db.query(Visita).filter(Visita.id == visita_id).first()
            if not visita_db:
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Visita con ID {visita_id} no encontrada.")

            cliente_id_str = str(visita_db.cliente_id)
            try:
                cliente_data = await self._get_cliente_data(cliente_id_str)
                nombre_cliente = cliente_data.get("nombre", "Cliente no encontrado")
                direccion_cliente = cliente_data.get("address", "Dirección no disponible")
            except HTTPException:
                nombre_cliente = "Cliente no disponible"
                direccion_cliente = "Dirección no disponible"

            visitas_anteriores_db = self.db.query(
                Visita.fecha_visita_programada, Visita.detalle
            ).filter(
                Visita.cliente_id == visita_db.cliente_id, 
                Visita.id != visita_id,                     
                Visita.detalle.isnot(None),             
                Visita.estado.in_(['REALIZADA', 'CANCELADA']) 
            ).order_by(desc(Visita.fecha_visita_programada)).limit(5).all() 
            
            notas_anteriores_list = [
                {"fecha_visita_programada": v.fecha_visita_programada, "detalle": v.detalle}
                for v in visitas_anteriores_db
            ]

            top_products_list = await self._get_top_products_data(cliente_id_str)

            visita_dict = visita_db.to_dict()
            visita_dict["nombre_institucion"] = nombre_cliente
            visita_dict["direccion"] = direccion_cliente
            visita_dict["notas_visitas_anteriores"] = notas_anteriores_list 
            visita_dict["productos_preferidos"] = top_products_list

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
            visita_db = self.db.query(Visita).filter(Visita.id == visita_id).first()
            if not visita_db:
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Visita con ID {visita_id} no encontrada.")
            update_data = data.model_dump(exclude_unset=True)
            if not update_data:
                raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="No se proporcionaron datos para actualizar.")

            nuevo_estado = update_data.get("estado")
            estado_actual = visita_db.estado
            
            if nuevo_estado:
                if estado_actual in ("REALIZADA", "CANCELADA") and nuevo_estado != estado_actual:
                    raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"No se puede cambiar el estado de una visita que ya está '{estado_actual}'.")
            
            for key, value in update_data.items():
                setattr(visita_db, key, value)
            
            self.db.add(visita_db)

            if nuevo_estado == "CANCELADA" and estado_actual != "CANCELADA":
                fecha_origen = visita_db.fecha_visita_programada
                if fecha_origen.tzinfo is None:
                    fecha_origen = fecha_origen.replace(tzinfo=timezone.utc)
                dia_semana = fecha_origen.weekday()
                dias_a_sumar = 1
                if dia_semana == 5: dias_a_sumar = 2
                elif dia_semana == 6: dias_a_sumar = 1
                fecha_nueva_base = fecha_origen + timedelta(days=dias_a_sumar)
                hora_aleatoria = random.randint(8, 18)
                minuto_aleatorio = random.choice([0, 15, 30, 45])
                fecha_reprogramada = fecha_nueva_base.replace(hour=hora_aleatoria, minute=minuto_aleatorio, second=0, microsecond=0)
                nueva_visita_reprogramada = Visita(
                    cliente_id=visita_db.cliente_id,
                    vendedor_id=visita_db.vendedor_id,
                    fecha_visita_programada=fecha_reprogramada,
                    estado="PENDIENTE"
                )
                self.db.add(nueva_visita_reprogramada)
                logger.info(f"Visita {visita_id} cancelada. Reprogramada para: {fecha_reprogramada}")

            self.db.commit()
            self.db.refresh(visita_db)
            return await self.get_visita_detalle_por_id(visita_id)
        except HTTPException as he:
            self.db.rollback()
            raise he
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar visita {visita_id}: {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Error interno al actualizar la visita.")

def get_visita_service(db: Session = Depends(get_db)) -> VisitaService:
    return VisitaService(db)