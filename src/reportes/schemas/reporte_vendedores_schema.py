from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class VendedorReporteItem(BaseModel):
    """Schema para un item del reporte de vendedores"""
    vendedor_id: str = Field(..., description="ID del vendedor")
    vendedor_nombre: str = Field(..., description="Nombre del vendedor")
    zona_asignada: str = Field(..., description="Zona asignada al vendedor")
    numero_pedidos: int = Field(..., description="Número de pedidos realizados en el periodo")
    porcentaje_meta: float = Field(..., description="Porcentaje de cumplimiento de la meta de ventas")
    ultima_actividad: Optional[datetime] = Field(None, description="Fecha y hora de la última actividad (último pedido)")
    meta_venta: Optional[Decimal] = Field(None, description="Meta de venta del plan asignado")
    ventas_totales: Decimal = Field(..., description="Total de ventas en el periodo")
    plan_venta_nombre: Optional[str] = Field(None, description="Nombre del plan de venta")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else 0.0
        }


class ReporteVendedoresResponse(BaseModel):
    """Schema de respuesta del reporte de vendedores"""
    vendedores: List[VendedorReporteItem] = Field(..., description="Lista de vendedores con sus métricas")
    total: int = Field(..., description="Total de vendedores en el reporte")
    fecha_inicio: datetime = Field(..., description="Fecha de inicio del periodo del reporte")
    fecha_fin: datetime = Field(..., description="Fecha de fin del periodo del reporte")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
