import pytest
from pydantic import ValidationError
from decimal import Decimal
from datetime import datetime

from schemas.plan_venta_schema import (
    CrearPlanVentaSchema,
    ActualizarPlanVentaSchema,
)
from schemas.vendedor_schema import ZonaAsignadaEnum


class TestCrearPlanVentaSchema:
    """Tests para el schema de creación de plan de venta"""

    def test_crear_plan_venta_schema_valido(self):
        """Test: Crear plan de venta con todos los datos válidos"""
        data = {
            "nombre": "Plan Q1 2024 - Perú",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "descripcion": "Plan de ventas del primer trimestre",
            "meta_venta": 100000.00,
            "zona_asignada": "Perú"
        }

        plan = CrearPlanVentaSchema(**data)

        assert plan.nombre == "Plan Q1 2024 - Perú"
        assert plan.descripcion == "Plan de ventas del primer trimestre"
        assert plan.meta_venta == Decimal("100000.00")
        assert plan.zona_asignada == ZonaAsignadaEnum.PERU

    def test_crear_plan_venta_sin_campos_opcionales(self):
        """Test: Crear plan de venta sin campos opcionales"""
        data = {
            "nombre": "Plan Q2 2024",
            "fecha_inicio": "2024-04-01T00:00:00",
            "fecha_fin": "2024-06-30T23:59:59",
            "meta_venta": 50000.00
        }

        plan = CrearPlanVentaSchema(**data)

        assert plan.nombre == "Plan Q2 2024"
        assert plan.descripcion is None
        assert plan.zona_asignada is None
        assert plan.meta_venta == Decimal("50000.00")

    def test_crear_plan_venta_nombre_vacio_falla(self):
        """Test: Fallar si el nombre está vacío"""
        data = {
            "nombre": "   ",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "meta_venta": 50000.00
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "nombre" in str(exc_info.value)

    def test_crear_plan_venta_fecha_fin_antes_de_inicio_falla(self):
        """Test: Fallar si fecha_fin es anterior a fecha_inicio"""
        data = {
            "nombre": "Plan Inválido",
            "fecha_inicio": "2024-12-31T00:00:00",
            "fecha_fin": "2024-01-01T00:00:00",  # Antes de fecha_inicio
            "meta_venta": 50000.00
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "fecha_fin" in str(exc_info.value)

    def test_crear_plan_venta_fecha_fin_igual_a_inicio_falla(self):
        """Test: Fallar si fecha_fin es igual a fecha_inicio"""
        fecha = "2024-01-01T00:00:00"
        data = {
            "nombre": "Plan Inválido",
            "fecha_inicio": fecha,
            "fecha_fin": fecha,
            "meta_venta": 50000.00
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "fecha_fin" in str(exc_info.value)

    def test_crear_plan_venta_meta_negativa_falla(self):
        """Test: Fallar si la meta de venta es negativa"""
        data = {
            "nombre": "Plan Inválido",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "meta_venta": -1000.00
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "meta_venta" in str(exc_info.value)

    def test_crear_plan_venta_meta_cero_falla(self):
        """Test: Fallar si la meta de venta es cero"""
        data = {
            "nombre": "Plan Inválido",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "meta_venta": 0
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "meta_venta" in str(exc_info.value)

    def test_crear_plan_venta_zona_invalida_falla(self):
        """Test: Fallar si la zona no es válida"""
        data = {
            "nombre": "Plan Inválido",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "meta_venta": 50000.00,
            "zona_asignada": "Argentina"  # No está en el enum
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        assert "zona_asignada" in str(exc_info.value)

    def test_crear_plan_venta_sin_campos_obligatorios_falla(self):
        """Test: Fallar si faltan campos obligatorios"""
        data = {
            "nombre": "Plan Incompleto"
            # Faltan: fecha_inicio, fecha_fin, meta_venta
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearPlanVentaSchema(**data)

        errors = str(exc_info.value)
        assert "fecha_inicio" in errors
        assert "fecha_fin" in errors
        assert "meta_venta" in errors

    def test_crear_plan_venta_descripcion_vacia_convierte_a_none(self):
        """Test: Convertir descripción vacía a None"""
        data = {
            "nombre": "Plan 2024",
            "fecha_inicio": "2024-01-01T00:00:00",
            "fecha_fin": "2024-03-31T23:59:59",
            "meta_venta": 50000.00,
            "descripcion": "   "  # Solo espacios
        }

        plan = CrearPlanVentaSchema(**data)

        assert plan.descripcion is None


class TestActualizarPlanVentaSchema:
    """Tests para el schema de actualización de plan de venta"""

    def test_actualizar_plan_venta_schema_valido(self):
        """Test: Actualizar plan de venta con datos válidos"""
        data = {
            "nombre": "Plan Q1 2024 - Actualizado",
            "meta_venta": 150000.00,
            "descripcion": "Meta incrementada"
        }

        plan = ActualizarPlanVentaSchema(**data)

        assert plan.nombre == "Plan Q1 2024 - Actualizado"
        assert plan.meta_venta == Decimal("150000.00")
        assert plan.descripcion == "Meta incrementada"

    def test_actualizar_plan_venta_todos_campos_opcionales(self):
        """Test: Todos los campos son opcionales en actualización"""
        data = {}

        plan = ActualizarPlanVentaSchema(**data)

        assert plan.nombre is None
        assert plan.fecha_inicio is None
        assert plan.fecha_fin is None
        assert plan.descripcion is None
        assert plan.meta_venta is None
        assert plan.zona_asignada is None

    def test_actualizar_plan_venta_nombre_vacio_falla(self):
        """Test: Fallar si el nombre está vacío"""
        data = {
            "nombre": "   "
        }

        with pytest.raises(ValidationError) as exc_info:
            ActualizarPlanVentaSchema(**data)

        assert "nombre" in str(exc_info.value)

    def test_actualizar_plan_venta_meta_negativa_falla(self):
        """Test: Fallar si la meta de venta es negativa"""
        data = {
            "meta_venta": -5000.00
        }

        with pytest.raises(ValidationError) as exc_info:
            ActualizarPlanVentaSchema(**data)

        assert "meta_venta" in str(exc_info.value)

    def test_actualizar_plan_venta_solo_un_campo(self):
        """Test: Actualizar solo un campo"""
        data = {
            "meta_venta": 200000.00
        }

        plan = ActualizarPlanVentaSchema(**data)

        assert plan.meta_venta == Decimal("200000.00")
        assert plan.nombre is None
        assert plan.fecha_inicio is None
