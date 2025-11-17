from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from db.database import get_db
from services.reporte_vendedores_service import ReporteVendedoresService
from schemas.reporte_vendedores_schema import ReporteVendedoresResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

reporte_vendedores_router = APIRouter()


@reporte_vendedores_router.get(
    "/vendedores",
    response_model=ReporteVendedoresResponse,
    summary="Generar reporte de vendedores",
    description="Genera un reporte con métricas de vendedores incluyendo número de pedidos, porcentaje de meta y última actividad"
)
def generar_reporte_vendedores(
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio del periodo del reporte. Por defecto: un mes atrás"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin del periodo del reporte. Por defecto: fecha actual"),
    zona_asignada: Optional[str] = Query(None, description="Filtrar por zona asignada"),
    db: Session = Depends(get_db)
):
    """
    Genera un reporte de vendedores con las siguientes métricas:
    - Vendedor y zona asignada
    - Número de pedidos en el periodo
    - Porcentaje de meta de su plan de ventas
    - Última actividad (último pedido)

    Si no se especifican fechas, se usa un rango por defecto:
    - fecha_inicio: un mes atrás desde hoy
    - fecha_fin: fecha actual
    """
    try:
        # Establecer fechas por defecto si no se proporcionan
        # Caso 1: No se proporcionan fechas -> último mes
        if fecha_inicio is None and fecha_fin is None:
            fecha_fin = datetime.now()
            fecha_inicio = fecha_fin - timedelta(days=30)
        # Caso 2: Solo se proporciona fecha_inicio -> desde fecha_inicio hasta hoy
        elif fecha_inicio is not None and fecha_fin is None:
            fecha_fin = datetime.now()
        # Caso 3: Solo se proporciona fecha_fin -> 30 días antes hasta fecha_fin
        elif fecha_inicio is None and fecha_fin is not None:
            fecha_inicio = fecha_fin - timedelta(days=30)
        # Caso 4: Se proporcionan ambas fechas -> usar las proporcionadas

        # Remover información de timezone para mantener consistencia
        if fecha_inicio and fecha_inicio.tzinfo is not None:
            fecha_inicio = fecha_inicio.replace(tzinfo=None)
        if fecha_fin and fecha_fin.tzinfo is not None:
            fecha_fin = fecha_fin.replace(tzinfo=None)

        # Normalizar fechas para cubrir el día completo
        # fecha_inicio: 00:00:00 del día
        # fecha_fin: 23:59:59.999999 del día
        fecha_inicio_normalizada = fecha_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin_normalizada = fecha_fin.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Validar fechas
        if fecha_fin_normalizada < fecha_inicio_normalizada:
            raise HTTPException(
                status_code=400,
                detail="La fecha de fin debe ser posterior a la fecha de inicio"
            )

        logger.info(f"Generando reporte de vendedores: {fecha_inicio_normalizada} - {fecha_fin_normalizada}")

        service = ReporteVendedoresService(db)
        reporte = service.generar_reporte(
            fecha_inicio=fecha_inicio_normalizada,
            fecha_fin=fecha_fin_normalizada,
            zona_asignada=zona_asignada
        )

        return reporte

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando reporte de vendedores: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el reporte: {str(e)}"
        )
