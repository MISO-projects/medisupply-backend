from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import logging

from db.vendedor_model import Vendedor
from db.plan_venta_model import PlanVenta
from db.orden_model import OrderProjection
from schemas.reporte_vendedores_schema import VendedorReporteItem, ReporteVendedoresResponse

logger = logging.getLogger(__name__)


class ReporteVendedoresService:
    """Servicio para generar reportes de vendedores"""

    def __init__(self, db: Session):
        self.db = db

    def generar_reporte(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        zona_asignada: Optional[str] = None
    ) -> ReporteVendedoresResponse:
        """
        Genera un reporte de vendedores con sus métricas de ventas.

        Args:
            fecha_inicio: Fecha de inicio del periodo
            fecha_fin: Fecha de fin del periodo
            zona_asignada: Filtro opcional por zona

        Returns:
            ReporteVendedoresResponse con la lista de vendedores y sus métricas
        """
        logger.info(f"Generando reporte de vendedores desde {fecha_inicio} hasta {fecha_fin}")

        # Construir query base para vendedores
        query = self.db.query(Vendedor).join(
            PlanVenta, Vendedor.plan_venta_id == PlanVenta.id
        )

        # Aplicar filtros
        if zona_asignada:
            query = query.filter(Vendedor.zona_asignada == zona_asignada)

        vendedores = query.all()
        logger.info(f"Encontrados {len(vendedores)} vendedores")

        # Generar métricas para cada vendedor
        vendedores_reporte = []
        for vendedor in vendedores:
            vendedor_metricas = self._calcular_metricas_vendedor(
                vendedor, fecha_inicio, fecha_fin
            )
            vendedores_reporte.append(vendedor_metricas)

        return ReporteVendedoresResponse(
            vendedores=vendedores_reporte,
            total=len(vendedores_reporte),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

    def _calcular_metricas_vendedor(
        self,
        vendedor: Vendedor,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> VendedorReporteItem:
        """
        Calcula las métricas de un vendedor para el periodo dado.

        Args:
            vendedor: Instancia del vendedor
            fecha_inicio: Fecha de inicio del periodo
            fecha_fin: Fecha de fin del periodo

        Returns:
            VendedorReporteItem con las métricas calculadas
        """
        # Obtener el plan de venta del vendedor
        plan_venta = self.db.query(PlanVenta).filter(
            PlanVenta.id == vendedor.plan_venta_id
        ).first()

        # Contar número de pedidos en el periodo
        query_pedidos = self.db.query(
            func.count(OrderProjection.id).label('numero_pedidos'),
            func.sum(OrderProjection.valor_total).label('ventas_totales'),
            func.max(OrderProjection.fecha_creacion).label('ultima_actividad')
        ).filter(
            and_(
                OrderProjection.id_vendedor == vendedor.id,
                OrderProjection.fecha_creacion >= fecha_inicio,
                OrderProjection.fecha_creacion <= fecha_fin
            )
        )

        resultado = query_pedidos.first()

        numero_pedidos = resultado.numero_pedidos if resultado.numero_pedidos else 0
        ventas_totales = Decimal(str(resultado.ventas_totales)) if resultado.ventas_totales else Decimal('0.0')
        ultima_actividad = resultado.ultima_actividad

        # Calcular porcentaje de meta
        meta_venta = plan_venta.meta_venta if plan_venta else Decimal('0.0')
        porcentaje_meta = 0.0

        if meta_venta and meta_venta > 0:
            porcentaje_meta = float((ventas_totales / meta_venta) * 100)

        return VendedorReporteItem(
            vendedor_id=str(vendedor.id),
            vendedor_nombre=vendedor.nombre,
            zona_asignada=vendedor.zona_asignada,
            numero_pedidos=numero_pedidos,
            porcentaje_meta=round(porcentaje_meta, 2),
            ultima_actividad=ultima_actividad,
            meta_venta=meta_venta,
            ventas_totales=ventas_totales,
            plan_venta_nombre=plan_venta.nombre if plan_venta else None
        )
