from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from typing import Optional
import logging

from services.reportes_service import ReportesService, get_reportes_service
from schemas.reporte_schema import ReporteVendedoresResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

reportes_router = APIRouter()


@reportes_router.get("/health")
def health_check(reportes_service: ReportesService = Depends(get_reportes_service)):
    return reportes_service.health_check()


@reportes_router.get(
    "/vendedores",
    response_model=ReporteVendedoresResponse,
    summary="Reporte de vendedores",
    description="Genera un reporte con métricas de vendedores incluyendo número de pedidos, porcentaje de meta y última actividad"
)
async def reporte_vendedores(
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio del periodo del reporte. Por defecto: un mes atrás"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin del periodo del reporte. Por defecto: fecha actual"),
    zona_asignada: Optional[str] = Query(None, description="Filtrar por zona asignada"),
    reportes_service: ReportesService = Depends(get_reportes_service)
):
    """
    Endpoint BFF para el reporte de vendedores.

    Retorna información de vendedores con sus métricas de ventas:
    - Nombre del vendedor
    - Zona asignada
    - Número de pedidos en el periodo
    - Porcentaje de meta de su plan de ventas
    - Última actividad (último pedido)

    Si no se especifican fechas, se usa un rango por defecto:
    - fecha_inicio: un mes atrás desde hoy
    - fecha_fin: fecha actual
    """
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

    logger.info(f"BFF: Solicitando reporte de vendedores {fecha_inicio} - {fecha_fin}")

    reporte = await reportes_service.generar_reporte_vendedores(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        zona_asignada=zona_asignada
    )

    return reporte

