from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
import os
from typing import List, Optional
import logging
from db.redis_client import RedisClient
from models.cliente_institucional_model import ClienteInstitucional
from schemas.cliente_schema import ClienteAsignadoResponse, ClienteAsignadoListResponse, ClientResponse
import json
from schemas.cliente_schema import RegisterRequest
import httpx  
import random  

AUTENTICACION_PATH = os.getenv("AUTENTICACION_SERVICE_URL", "http://autenticacion-service:3000")
VENTAS_PATH = os.getenv("VENTAS_SERVICE_URL", "http://ventas-service:3000")
VISITAS_PATH = os.getenv("VISITAS_SERVICE_URL", "http://visitas-service:3000") 

logger = logging.getLogger(__name__)


class ClienteService:
    def __init__(self, db: Session, redis_client: RedisClient):
        self.db = db
        self.redis_client = redis_client

    def get_all_clients(self, db: Session) -> List[ClientResponse]:
        try:
            clientes_db = db.query(ClienteInstitucional).all()
            clientes_response = [
                ClientResponse(
                    id=str(cliente.id),
                    nombre=cliente.nombre,
                    nit=cliente.nit,
                    logoUrl=cliente.logo_url,
                    address=cliente.address,
                    fecha_creacion=cliente.fecha_creacion,
                    fecha_actualizacion=cliente.fecha_actualizacion,
                    id_vendedor=str(cliente.id_vendedor) if cliente.id_vendedor else None
                )
                for cliente in clientes_db
            ]
            return clientes_response
        except Exception as e:
            logger.error(f"Error al obtener lista de clientes: {str(e)}")
            raise
    

    def get_clientes_asignados(self, vendedor_id: str, use_cache: bool = True) -> ClienteAsignadoListResponse:

        try:
            if use_cache:
                cached_data = self._get_from_cache(vendedor_id)
                if cached_data:
                    logger.info(f"Clientes obtenidos desde cache para vendedor {vendedor_id}")
                    return cached_data

            clientes_db = self.db.query(ClienteInstitucional).filter(
                ClienteInstitucional.id_vendedor == vendedor_id
            ).all()

            clientes_response = [
                ClienteAsignadoResponse(
                    id=str(cliente.id),
                    nombre=cliente.nombre,
                    nit=cliente.nit,
                    logoUrl=cliente.logo_url
                )
                for cliente in clientes_db
            ]

            response = ClienteAsignadoListResponse(
                clientes=clientes_response,
                total=len(clientes_response)
            )

            if use_cache:
                self._save_to_cache(vendedor_id, response)

            logger.info(f"Se encontraron {len(clientes_response)} clientes para vendedor {vendedor_id}")
            return response

        except Exception as e:
            logger.error(f"Error al obtener clientes asignados para vendedor {vendedor_id}: {str(e)}")
            raise

    def _get_from_cache(self, vendedor_id: str) -> Optional[ClienteAsignadoListResponse]:
        try:
            if not self.redis_client.is_connected():
                return None

            cache_key = f"clientes_asignados:{vendedor_id}"
            cached_data = self.redis_client.client.get(cache_key)
            
            if cached_data:
                data_dict = json.loads(cached_data)
                return ClienteAsignadoListResponse(**data_dict)
            
            return None
        except Exception as e:
            logger.warning(f"Error al obtener datos del cache: {str(e)}")
            return None

    def _save_to_cache(self, vendedor_id: str, data: ClienteAsignadoListResponse, ttl: int = 300):
        try:
            if not self.redis_client.is_connected():
                return

            cache_key = f"clientes_asignados:{vendedor_id}"
            data_json = data.model_dump_json()
            
            self.redis_client.client.setex(cache_key, ttl, data_json)
            logger.info(f"Datos guardados en cache para vendedor {vendedor_id} con TTL {ttl}s")
            
        except Exception as e:
            logger.warning(f"Error al guardar datos en cache: {str(e)}")

    def invalidate_cache(self, vendedor_id: str):
        try:
            if not self.redis_client.is_connected():
                return

            cache_key = f"clientes_asignados:{vendedor_id}"
            self.redis_client.client.delete(cache_key)
            logger.info(f"Cache invalidado para vendedor {vendedor_id}")
            
        except Exception as e:
            logger.warning(f"Error al invalidar cache: {str(e)}")

    def get_cliente_by_id(self, cliente_id: str, vendedor_id: str) -> Optional[ClienteAsignadoResponse]:

        try:
            cliente_db = self.db.query(ClienteInstitucional).filter(
                and_(
                    ClienteInstitucional.id == cliente_id,
                    ClienteInstitucional.id_vendedor == vendedor_id
                )
            ).first()

            if not cliente_db:
                return None

            return ClienteAsignadoResponse(
                id=str(cliente_db.id),
                nombre=cliente_db.nombre,
                nit=cliente_db.nit,
                logoUrl=cliente_db.logo_url
            )

        except Exception as e:
            logger.error(f"Error al obtener cliente {cliente_id} para vendedor {vendedor_id}: {str(e)}")
            raise

    def get_clientes_by_ids(self, cliente_ids: List[str]) -> List[ClientResponse]:
        """
        Obtiene múltiples clientes por sus IDs.
        
        Args:
            cliente_ids: Lista de IDs de clientes
            
        Returns:
            Lista de ClientResponse con los datos de los clientes encontrados
            
        Raises:
            HTTPException: Si hay un error al procesar la solicitud
        """
        try:
            if not cliente_ids:
                return []
            
            clientes_db = self.db.query(ClienteInstitucional).filter(
                ClienteInstitucional.id.in_(cliente_ids)
            ).all()

            clientes_response = [
                ClientResponse(
                    id=str(cliente.id),
                    nombre=cliente.nombre,
                    nit=cliente.nit,
                    logoUrl=cliente.logo_url,
                    address=cliente.address,
                    fecha_creacion=cliente.fecha_creacion,
                    fecha_actualizacion=cliente.fecha_actualizacion,
                    id_vendedor=str(cliente.id_vendedor) if cliente.id_vendedor else None
                )
                for cliente in clientes_db
            ]

            logger.info(f"Se encontraron {len(clientes_response)} clientes de {len(cliente_ids)} IDs solicitados")
            return clientes_response

        except Exception as e:
            logger.error(f"Error al obtener clientes por IDs: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener los clientes."
            )

    def get_cliente_info(self, cliente_id: str) -> ClientResponse:
        """
        Obtiene la información de un cliente por su ID.
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            ClientResponse con los datos del cliente
            
        Raises:
            HTTPException 404: Si el cliente no existe
            HTTPException 500: Si hay un error al procesar la solicitud
        """
        try:
            cliente_db = self.db.query(ClienteInstitucional).filter(
                ClienteInstitucional.id == cliente_id
            ).first()

            if not cliente_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado"
                )

            return ClientResponse(
                id=str(cliente_db.id),
                nombre=cliente_db.nombre,
                nit=cliente_db.nit,
                logoUrl=cliente_db.logo_url,
                address=cliente_db.address,
                fecha_creacion=cliente_db.fecha_creacion,
                fecha_actualizacion=cliente_db.fecha_actualizacion,
                id_vendedor=str(cliente_db.id_vendedor) if cliente_db.id_vendedor else None
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener información del cliente {cliente_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener la información del cliente."
            )

    def register_client(self, db: Session, register_data: RegisterRequest) -> ClientResponse: 
        # 1️⃣ Llamar al servicio de autenticación para traer los vendedores activos
        try:
            response = httpx.get(f"{VENTAS_PATH}/vendedores/", timeout=30.0)
            response.raise_for_status()
            response_json = response.json() 
            sellers_list = response_json.get('data', [])
            sellers_ids = [seller.get('id') for seller in sellers_list if seller.get('id')]
        except Exception as e:
            logger.error(f"Error al obtener vendedores activos: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudieron obtener los vendedores activos"
            )

        # 2️⃣ Escoger uno al azar
        if not sellers_ids:
            raise HTTPException(status_code=400, detail="No hay vendedores creados para asignar al cliente.")
        id_vendedor = random.choice(sellers_ids)

        # 3️⃣ Crear el cliente con ese vendedor
        new_client = ClienteInstitucional(
            nombre=register_data.nombre,
            nit=register_data.nit,
            id_vendedor=id_vendedor,
            address=register_data.address,
            logo_url=getattr(register_data, 'logoUrl', None)
        )

        try:
            db.add(new_client)
            db.commit()
            db.refresh(new_client)
            
            try:
                visita_payload = {"cliente_id": str(new_client.id)}
                visita_url = f"{VISITAS_PATH}/api/visitas/"
                
                response = httpx.post(visita_url, json=visita_payload, timeout=5.0)
                response.raise_for_status() # Lanza error si es 4xx o 5xx
                
                logger.info(f"Visita inicial creada exitosamente para cliente {new_client.id}")
            
            except Exception as e:
                logger.error(f"Error al crear la visita inicial para el cliente {new_client.id}: {e}")

            try:
                self.invalidate_cache(str(id_vendedor))
                logger.info(f"Cache invalidado para vendedor {id_vendedor} tras registro de cliente.")
            except Exception as e:
                logger.error(f"Error al invalidar caché para {id_vendedor}: {e}")
            user_dict = new_client.to_dict()
            return ClientResponse(**user_dict)

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nit ya está registrado"
            )

def get_client_service() -> ClienteService:
    """
    Función de dependencia para inyectar el servicio de cliente

    Returns:
        AuthService: Instancia del servicio de cleinte
    """
    return ClienteService()