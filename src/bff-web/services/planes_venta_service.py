import httpx
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class PlanesVentaService:
    """Service for communicating with the Ventas microservice (Planes de Venta endpoints)"""

    def __init__(self):
        self.base_url = os.getenv("VENTAS_SERVICE_URL", "http://ventas-service:3000")
        self.timeout = 30.0

    async def crear_plan_venta(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new plan de venta via the ventas service"""
        try:
            # Convert Decimal to float for JSON serialization
            if 'meta_venta' in plan_data and plan_data['meta_venta'] is not None:
                plan_data['meta_venta'] = float(plan_data['meta_venta'])

            # Convert datetime to ISO string
            if 'fecha_inicio' in plan_data and plan_data['fecha_inicio'] is not None:
                plan_data['fecha_inicio'] = plan_data['fecha_inicio'].isoformat()
            if 'fecha_fin' in plan_data and plan_data['fecha_fin'] is not None:
                plan_data['fecha_fin'] = plan_data['fecha_fin'].isoformat()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/planes-venta/",
                    json=plan_data
                )

                if response.status_code == 201:
                    return response.json()
                elif response.status_code == 409:
                    raise HTTPException(status_code=409, detail=response.json())
                elif response.status_code == 422:
                    raise HTTPException(status_code=422, detail=response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def listar_planes_venta(
        self,
        page: int = 1,
        page_size: int = 20,
        nombre: Optional[str] = None,
        zona_asignada: Optional[str] = None
    ) -> Dict[str, Any]:
        """List planes de venta with pagination and optional filters"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }

            if nombre:
                params["nombre"] = nombre
            if zona_asignada:
                params["zona_asignada"] = zona_asignada

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/planes-venta/",
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def obtener_plan_venta(self, plan_id: str) -> Dict[str, Any]:
        """Get a specific plan de venta by ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/planes-venta/{plan_id}"
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Plan de venta no encontrado")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def actualizar_plan_venta(
        self,
        plan_id: str,
        plan_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing plan de venta"""
        try:
            # Convert Decimal to float for JSON serialization
            if 'meta_venta' in plan_data and plan_data['meta_venta'] is not None:
                plan_data['meta_venta'] = float(plan_data['meta_venta'])

            # Convert datetime to ISO string
            if 'fecha_inicio' in plan_data and plan_data['fecha_inicio'] is not None:
                plan_data['fecha_inicio'] = plan_data['fecha_inicio'].isoformat()
            if 'fecha_fin' in plan_data and plan_data['fecha_fin'] is not None:
                plan_data['fecha_fin'] = plan_data['fecha_fin'].isoformat()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/planes-venta/{plan_id}",
                    json=plan_data
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Plan de venta no encontrado")
                elif response.status_code == 409:
                    raise HTTPException(status_code=409, detail=response.json())
                elif response.status_code == 422:
                    raise HTTPException(status_code=422, detail=response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def eliminar_plan_venta(self, plan_id: str) -> Dict[str, Any]:
        """Delete a plan de venta"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/planes-venta/{plan_id}"
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Plan de venta no encontrado")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )


def get_planes_venta_service() -> PlanesVentaService:
    """Dependency function to get planes de venta service instance"""
    return PlanesVentaService()
