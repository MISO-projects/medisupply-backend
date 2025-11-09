from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status
from typing import List, Tuple, Optional, Dict, Any
import logging
import math
from db.redis_client import RedisClient
from models.ruta_model import Ruta, Parada, Conductor, Vehiculo
from db.order_projection_model import OrderProjection, ClienteInstitucional
from schemas.ruta_schema import (
    RutaCreateRequest, 
    RutaCreateResponse, 
    RutaResponse,
    RutasListResponse,
    ParadaResponse,
    PedidoInfo
)
from services.traffic_manager import optimize_route_order, TrafficAPIManager

logger = logging.getLogger(__name__)


class RutaService:
    def __init__(self, db: Session, redis_client: RedisClient = None):
        self.db = db
        self.redis_client = redis_client

    def _get_pedido_info(self, pedido_id: str) -> Optional[PedidoInfo]:
        """
        Obtiene información del pedido desde order_projections.
        
        Args:
            pedido_id: UUID del pedido
            
        Returns:
            PedidoInfo con datos del pedido o None si no se encuentra
        """
        try:
            # Consultar el pedido
            orden = self.db.query(OrderProjection).filter(
                OrderProjection.id == pedido_id
            ).first()
            
            if not orden:
                logger.warning(f"Pedido {pedido_id} no encontrado en order_projections")
                return None
            
            # Obtener nombre del cliente
            nombre_cliente = None
            if orden.id_cliente:
                cliente = self.db.query(ClienteInstitucional).filter(
                    ClienteInstitucional.id == orden.id_cliente
                ).first()
                if cliente:
                    nombre_cliente = cliente.nombre
            
            return PedidoInfo(
                numero_orden=orden.numero_orden,
                estado=orden.estado,
                valor_total=float(orden.valor_total) if orden.valor_total else None,
                cantidad_items=orden.cantidad_items,
                nombre_cliente=nombre_cliente
            )
        except Exception as e:
            logger.warning(f"Error al obtener información del pedido {pedido_id}: {e}")
            return None

    def crear_ruta(self, ruta_data: RutaCreateRequest) -> RutaCreateResponse:

        try:
            # Verificar que el conductor exista
            conductor = self.db.query(Conductor).filter(Conductor.id == ruta_data.conductor_id).first()
            if not conductor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El conductor con ID {ruta_data.conductor_id} no existe"
                )
            
            # Verificar que el vehículo exista
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta_data.vehiculo_id).first()
            if not vehiculo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El vehículo con ID {ruta_data.vehiculo_id} no existe"
                )
            
            # Crear la ruta
            nueva_ruta = Ruta(
                fecha=ruta_data.fecha,
                bodega_origen=ruta_data.bodega_origen,
                estado=ruta_data.estado,
                vehiculo_id=ruta_data.vehiculo_id,
                conductor_id=ruta_data.conductor_id,
                condiciones_almacenamiento=ruta_data.condiciones_almacenamiento
            )
            
            self.db.add(nueva_ruta)
            self.db.flush() 
            
            logger.info(f"Ruta creada con ID: {nueva_ruta.id}")
            
            paradas_ordenadas = self._optimizar_orden_paradas(ruta_data.paradas, ruta_data.bodega_origen)
            
            for idx, parada_data in enumerate(paradas_ordenadas, start=1):
                nueva_parada = Parada(
                    ruta_id=nueva_ruta.id,
                    pedido_id=parada_data.pedido_id,
                    direccion=parada_data.direccion,
                    contacto=parada_data.contacto,
                    latitud=parada_data.latitud,
                    longitud=parada_data.longitud,
                    orden=parada_data.orden if parada_data.orden is not None else idx
                )
                self.db.add(nueva_parada)
            
            # Confirmar la transacción
            self.db.commit()
            self.db.refresh(nueva_ruta)
            
            logger.info(f"Ruta {nueva_ruta.id} creada exitosamente con {len(ruta_data.paradas)} paradas")
            
            return RutaCreateResponse(
                id=nueva_ruta.id,
                mensaje="Ruta creada exitosamente"
            )
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear ruta: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de integridad de datos al crear la ruta"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error de base de datos al crear ruta: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la ruta en la base de datos"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inesperado al crear ruta: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al crear la ruta: {str(e)}"
            )

    def obtener_ruta(self, ruta_id: int) -> RutaResponse:

        try:
            ruta = self.db.query(Ruta).options(
                joinedload(Ruta.conductor),
                joinedload(Ruta.vehiculo),
                joinedload(Ruta.paradas)
            ).filter(Ruta.id == ruta_id).first()
            
            if not ruta:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ruta con ID {ruta_id} no encontrada"
                )
            
            # Construir la respuesta con las paradas ordenadas por el campo orden
            paradas_ordenadas = sorted(ruta.paradas, key=lambda p: p.orden if p.orden is not None else 999)
            paradas_response = [
                ParadaResponse(
                    id=parada.id,
                    ruta_id=parada.ruta_id,
                    pedido_id=parada.pedido_id,
                    pedido=self._get_pedido_info(parada.pedido_id),
                    direccion=parada.direccion,
                    contacto=parada.contacto,
                    latitud=float(parada.latitud) if parada.latitud else None,
                    longitud=float(parada.longitud) if parada.longitud else None,
                    orden=parada.orden,
                    estado=parada.estado,
                    fecha_creacion=parada.fecha_creacion,
                    fecha_actualizacion=parada.fecha_actualizacion
                )
                for parada in paradas_ordenadas
            ]
            
            return RutaResponse(
                id=ruta.id,
                fecha=ruta.fecha,
                bodega_origen=ruta.bodega_origen,
                estado=ruta.estado,
                vehiculo_id=ruta.vehiculo_id,
                conductor_id=ruta.conductor_id,
                vehiculo_placa=ruta.vehiculo.placa if ruta.vehiculo else None,
                vehiculo_info=f"{ruta.vehiculo.marca} {ruta.vehiculo.modelo}" if ruta.vehiculo else None,
                conductor_nombre=f"{ruta.conductor.nombre} {ruta.conductor.apellido}" if ruta.conductor else None,
                condiciones_almacenamiento=ruta.condiciones_almacenamiento,
                fecha_creacion=ruta.fecha_creacion,
                fecha_actualizacion=ruta.fecha_actualizacion,
                paradas=paradas_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener ruta {ruta_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener la ruta: {str(e)}"
            )

    def _get_bodega_coords(self, bodega_origen: str) -> Tuple[float, float]:
    
        
        DEFAULT_COORDS = (4.6097, -74.0817)
        
        
        logger.info(f"Usando coordenadas para bodega: {bodega_origen}")
        return DEFAULT_COORDS
    
    def _optimizar_orden_paradas(
        self, 
        paradas: List, 
        bodega_origen: str
    ) -> List:
       
        paradas_con_coordenadas = [
            p for p in paradas 
            if p.latitud is not None and p.longitud is not None
        ]
        
        tiene_orden_explicito = any(p.orden is not None for p in paradas)
        
        if len(paradas_con_coordenadas) != len(paradas) or tiene_orden_explicito:
            if len(paradas_con_coordenadas) != len(paradas):
                logger.info("No todas las paradas tienen coordenadas, usando orden original")
            else:
                logger.info("Orden explícito especificado, respetando orden del usuario")
            return paradas
        
        if len(paradas_con_coordenadas) < 2:
            logger.info("Menos de 2 paradas, no se requiere optimización")
            return paradas
        
        try:
            origin_coords = self._get_bodega_coords(bodega_origen)
            
            stops_coords = [
                (p.latitud, p.longitud) 
                for p in paradas_con_coordenadas
            ]
            
            logger.info(f"Optimizando orden de {len(stops_coords)} paradas usando OSRM")
            optimized_indices = optimize_route_order(origin_coords, stops_coords)
            
            # Reordenar las paradas según el orden optimizado
            paradas_optimizadas = [paradas_con_coordenadas[i] for i in optimized_indices]
            
            logger.info(f"Orden optimizado aplicado exitosamente")
            return paradas_optimizadas
            
        except Exception as e:
            logger.warning(f"Error al optimizar orden de paradas: {str(e)}. Usando orden original.")
            return paradas

    def listar_rutas(self, page: int = 1, page_size: int = 20) -> RutasListResponse:

        try:
            skip = (page - 1) * page_size
            
            total = self.db.query(Ruta).count()
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            
            rutas = self.db.query(Ruta).options(
                joinedload(Ruta.conductor),
                joinedload(Ruta.vehiculo),
                joinedload(Ruta.paradas)
            ).order_by(Ruta.fecha.asc()).offset(skip).limit(page_size).all()
            
            rutas_response = [
                RutaResponse(
                    id=ruta.id,
                    fecha=ruta.fecha,
                    bodega_origen=ruta.bodega_origen,
                    estado=ruta.estado,
                    vehiculo_id=ruta.vehiculo_id,
                    conductor_id=ruta.conductor_id,
                    vehiculo_placa=ruta.vehiculo.placa if ruta.vehiculo else None,
                    vehiculo_info=f"{ruta.vehiculo.marca} {ruta.vehiculo.modelo}" if ruta.vehiculo else None,
                    conductor_nombre=f"{ruta.conductor.nombre} {ruta.conductor.apellido}" if ruta.conductor else None,
                    condiciones_almacenamiento=ruta.condiciones_almacenamiento,
                    fecha_creacion=ruta.fecha_creacion,
                    fecha_actualizacion=ruta.fecha_actualizacion,
                    paradas=[
                        ParadaResponse(
                            id=parada.id,
                            ruta_id=parada.ruta_id,
                            pedido_id=parada.pedido_id,
                            pedido=self._get_pedido_info(parada.pedido_id),
                            direccion=parada.direccion,
                            contacto=parada.contacto,
                            latitud=float(parada.latitud) if parada.latitud else None,
                            longitud=float(parada.longitud) if parada.longitud else None,
                            orden=parada.orden,
                            estado=parada.estado,
                            fecha_creacion=parada.fecha_creacion,
                            fecha_actualizacion=parada.fecha_actualizacion
                        )
                        for parada in sorted(ruta.paradas, key=lambda p: p.orden if p.orden is not None else 999)
                    ]
                )
                for ruta in rutas
            ]
            
            return RutasListResponse(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                rutas=rutas_response
            )
            
        except Exception as e:
            logger.error(f"Error al listar rutas: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al listar las rutas: {str(e)}"
            )

    def obtener_entregas_por_cliente(
        self, 
        id_cliente: str, 
        estado_parada: Optional[str] = None,
        estado_ruta: Optional[str] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Obtiene todas las entregas programadas (paradas) para un cliente específico.
        
        Args:
            id_cliente: UUID del cliente
            estado_parada: Filtro opcional por estado de parada
            estado_ruta: Filtro opcional por estado de ruta
            page: Número de página
            page_size: Tamaño de página
            
        Returns:
            Dict con paradas paginadas y sus rutas asociadas
        """
        try:
            # Primero obtener todas las órdenes del cliente desde order_projections
            ordenes_cliente = self.db.query(OrderProjection.id).filter(
                OrderProjection.id_cliente == id_cliente
            ).all()
            
            if not ordenes_cliente:
                return {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }
            
            # Extraer los IDs de las órdenes
            order_ids = [str(orden.id) for orden in ordenes_cliente]
            
            # Consultar paradas que coincidan con esos pedidos
            query = self.db.query(Parada).options(
                joinedload(Parada.ruta).joinedload(Ruta.conductor),
                joinedload(Parada.ruta).joinedload(Ruta.vehiculo)
            ).filter(Parada.pedido_id.in_(order_ids))
            
            # Aplicar filtros opcionales
            if estado_parada:
                query = query.filter(Parada.estado == estado_parada)
            
            if estado_ruta:
                query = query.join(Ruta).filter(Ruta.estado == estado_ruta)
            
            # Contar total antes de paginar
            total = query.count()
            
            # Aplicar paginación
            skip = (page - 1) * page_size
            paradas = query.order_by(Parada.fecha_creacion.desc()).offset(skip).limit(page_size).all()
            
            # Construir respuesta
            entregas = []
            for parada in paradas:
                pedido_info = self._get_pedido_info(parada.pedido_id)
                
                entrega = {
                    "parada": {
                        "id": parada.id,
                        "pedido_id": parada.pedido_id,
                        "direccion": parada.direccion,
                        "contacto": parada.contacto,
                        "latitud": float(parada.latitud) if parada.latitud else None,
                        "longitud": float(parada.longitud) if parada.longitud else None,
                        "orden": parada.orden,
                        "estado": parada.estado,
                        "fecha_creacion": parada.fecha_creacion.isoformat(),
                        "fecha_actualizacion": parada.fecha_actualizacion.isoformat()
                    },
                    "pedido": pedido_info.dict() if pedido_info else None,
                    "ruta": {
                        "id": parada.ruta.id,
                        "fecha": parada.ruta.fecha,
                        "bodega_origen": parada.ruta.bodega_origen,
                        "estado": parada.ruta.estado,
                        "vehiculo_placa": parada.ruta.vehiculo.placa if parada.ruta.vehiculo else None,
                        "vehiculo_info": f"{parada.ruta.vehiculo.marca} {parada.ruta.vehiculo.modelo}" if parada.ruta.vehiculo else None,
                        "conductor_nombre": f"{parada.ruta.conductor.nombre} {parada.ruta.conductor.apellido}" if parada.ruta.conductor else None,
                        "condiciones_almacenamiento": parada.ruta.condiciones_almacenamiento
                    } if parada.ruta else None
                }
                entregas.append(entrega)
            
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            
            return {
                "data": entregas,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Error al obtener entregas del cliente {id_cliente}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener entregas programadas: {str(e)}"
            )


def get_ruta_service(
    db: Session,
    redis_client: RedisClient = None
) -> RutaService:
    return RutaService(db=db, redis_client=redis_client)

