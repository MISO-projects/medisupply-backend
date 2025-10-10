from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
import logging
from db.redis_client import RedisClient
from models.cliente_institucional_model import ClienteInstitucional
from schemas.cliente_schema import ClienteAsignadoResponse, ClienteAsignadoListResponse
import json

logger = logging.getLogger(__name__)


class ClienteService:
    def __init__(self, db: Session, redis_client: RedisClient):
        self.db = db
        self.redis_client = redis_client

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
