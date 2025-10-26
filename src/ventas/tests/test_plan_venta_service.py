import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException
from decimal import Decimal
from datetime import datetime

from services.plan_venta_service import PlanVentaService
from schemas.plan_venta_schema import CrearPlanVentaSchema, ActualizarPlanVentaSchema
from schemas.vendedor_schema import ZonaAsignadaEnum
from db.plan_venta_model import PlanVenta


class TestPlanVentaServiceCrear:
    """Tests para crear plan de venta"""

    def test_crear_plan_venta_exitoso(self):
        """Test: Crear plan de venta exitosamente"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None  # No existe plan con ese nombre
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        plan_data = CrearPlanVentaSchema(
            nombre="Plan Q1 2024 - Perú",
            fecha_inicio=datetime(2024, 1, 1),
            fecha_fin=datetime(2024, 3, 31),
            descripcion="Plan trimestral",
            meta_venta=Decimal("100000.00"),
            zona_asignada=ZonaAsignadaEnum.PERU
        )

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.crear_plan_venta(plan_data)

        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert "nombre" in result
        assert result["nombre"] == "Plan Q1 2024 - Perú"

    def test_crear_plan_venta_sin_campos_opcionales(self):
        """Test: Crear plan de venta sin campos opcionales"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None  # No existe plan con ese nombre
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        plan_data = CrearPlanVentaSchema(
            nombre="Plan Q2 2024",
            fecha_inicio=datetime(2024, 4, 1),
            fecha_fin=datetime(2024, 6, 30),
            meta_venta=Decimal("50000.00")
        )

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.crear_plan_venta(plan_data)

        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_crear_plan_venta_nombre_duplicado_falla(self):
        """Test: Fallar al crear plan de venta con nombre duplicado"""
        # Arrange
        mock_db = Mock()

        # Simular que ya existe un plan con ese nombre
        plan_existente = Mock()
        plan_existente.nombre = "Plan Q1 2024"
        mock_db.query().filter().first.return_value = plan_existente

        plan_data = CrearPlanVentaSchema(
            nombre="Plan Q1 2024",
            fecha_inicio=datetime(2024, 1, 1),
            fecha_fin=datetime(2024, 3, 31),
            meta_venta=Decimal("100000.00")
        )

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.crear_plan_venta(plan_data)

        assert exc_info.value.status_code == 409
        assert "nombre" in str(exc_info.value.detail).lower()


class TestPlanVentaServiceObtener:
    """Tests para obtener plan de venta"""

    def test_obtener_plan_venta_existente(self):
        """Test: Obtener plan de venta que existe"""
        # Arrange
        mock_db = Mock()

        plan_mock = Mock()
        plan_mock.to_dict.return_value = {
            "id": "123",
            "nombre": "Plan Q1 2024",
            "meta_venta": "100000.00",
            "zona_asignada": "Perú"
        }

        mock_db.query().filter().first.return_value = plan_mock

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.obtener_plan_venta("123")

        # Assert
        assert result["id"] == "123"
        assert result["nombre"] == "Plan Q1 2024"

    def test_obtener_plan_venta_no_existente_falla(self):
        """Test: Fallar al obtener plan de venta que no existe"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.obtener_plan_venta("999")

        assert exc_info.value.status_code == 404


class TestPlanVentaServiceListar:
    """Tests para listar planes de venta"""

    def test_listar_planes_venta_exitoso(self):
        """Test: Listar planes de venta exitosamente"""
        # Arrange
        mock_db = Mock()

        plan1 = Mock()
        plan1.to_dict.return_value = {"id": "1", "nombre": "Plan Q1"}

        plan2 = Mock()
        plan2.to_dict.return_value = {"id": "2", "nombre": "Plan Q2"}

        mock_query = Mock()
        mock_query.filter().order_by().offset().limit().all.return_value = [plan1, plan2]
        mock_query.order_by().offset().limit().all.return_value = [plan1, plan2]
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.listar_planes_venta(skip=0, limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]["nombre"] == "Plan Q1"
        assert result[1]["nombre"] == "Plan Q2"

    def test_listar_planes_venta_con_filtro_zona(self):
        """Test: Listar planes de venta filtrados por zona"""
        # Arrange
        mock_db = Mock()

        plan1 = Mock()
        plan1.to_dict.return_value = {"id": "1", "nombre": "Plan Perú", "zona_asignada": "Perú"}

        mock_query = Mock()
        mock_query.filter().order_by().offset().limit().all.return_value = [plan1]
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.listar_planes_venta(skip=0, limit=10, zona_asignada="Perú")

        # Assert
        assert len(result) == 1
        assert result[0]["zona_asignada"] == "Perú"

    def test_listar_planes_venta_vacio(self):
        """Test: Listar planes de venta cuando no hay ninguno"""
        # Arrange
        mock_db = Mock()

        mock_query = Mock()
        mock_query.order_by().offset().limit().all.return_value = []
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.listar_planes_venta(skip=0, limit=10)

        # Assert
        assert len(result) == 0


class TestPlanVentaServiceActualizar:
    """Tests para actualizar plan de venta"""

    def test_actualizar_plan_venta_exitoso(self):
        """Test: Actualizar plan de venta exitosamente"""
        # Arrange
        mock_db = Mock()

        plan_mock = Mock()
        plan_mock.id = "123"
        plan_mock.nombre = "Plan Q1 2024"
        plan_mock.fecha_inicio = datetime(2024, 1, 1)
        plan_mock.fecha_fin = datetime(2024, 3, 31)
        plan_mock.to_dict.return_value = {
            "id": "123",
            "nombre": "Plan Q1 2024 - Actualizado",
            "meta_venta": "150000.00"
        }

        # Primera llamada: encontrar el plan a actualizar
        # Segunda llamada: verificar si el nuevo nombre existe (debe retornar None)
        mock_db.query().filter().first.side_effect = [plan_mock, None]
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        plan_data = ActualizarPlanVentaSchema(
            nombre="Plan Q1 2024 - Actualizado",
            meta_venta=Decimal("150000.00")
        )

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.actualizar_plan_venta("123", plan_data)

        # Assert
        assert mock_db.commit.called
        assert result["nombre"] == "Plan Q1 2024 - Actualizado"

    def test_actualizar_plan_venta_no_existente_falla(self):
        """Test: Fallar al actualizar plan de venta que no existe"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        plan_data = ActualizarPlanVentaSchema(nombre="Nuevo Nombre")

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_plan_venta("999", plan_data)

        assert exc_info.value.status_code == 404

    def test_actualizar_plan_venta_fechas_invalidas_falla(self):
        """Test: Fallar al actualizar con fecha_fin antes de fecha_inicio"""
        # Arrange
        mock_db = Mock()

        plan_mock = Mock()
        plan_mock.id = "123"
        plan_mock.fecha_inicio = datetime(2024, 1, 1)
        plan_mock.fecha_fin = datetime(2024, 3, 31)

        mock_db.query().filter().first.return_value = plan_mock

        # Intentar actualizar fecha_fin a una fecha anterior a fecha_inicio
        plan_data = ActualizarPlanVentaSchema(
            fecha_fin=datetime(2023, 12, 31)  # Antes de fecha_inicio
        )

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_plan_venta("123", plan_data)

        assert exc_info.value.status_code == 400

    def test_actualizar_plan_venta_nombre_duplicado_falla(self):
        """Test: Fallar al actualizar con nombre que ya existe en otro plan"""
        # Arrange
        mock_db = Mock()

        plan_actual = Mock()
        plan_actual.id = "123"
        plan_actual.nombre = "Plan Q1 2024"
        plan_actual.fecha_inicio = datetime(2024, 1, 1)
        plan_actual.fecha_fin = datetime(2024, 3, 31)

        otro_plan = Mock()
        otro_plan.id = "456"
        otro_plan.nombre = "Plan Q2 2024"

        # Primera llamada: encontrar el plan a actualizar
        # Segunda llamada: verificar si el nuevo nombre ya existe
        mock_db.query().filter().first.side_effect = [plan_actual, otro_plan]

        plan_data = ActualizarPlanVentaSchema(
            nombre="Plan Q2 2024"  # Nombre que ya existe en otro plan
        )

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_plan_venta("123", plan_data)

        assert exc_info.value.status_code == 409
        assert "nombre" in str(exc_info.value.detail).lower()


class TestPlanVentaServiceEliminar:
    """Tests para eliminar plan de venta"""

    def test_eliminar_plan_venta_exitoso(self):
        """Test: Eliminar plan de venta exitosamente"""
        # Arrange
        mock_db = Mock()

        plan_mock = Mock()
        plan_mock.id = "123"

        mock_db.query().filter().first.return_value = plan_mock
        mock_db.delete = Mock()
        mock_db.commit = Mock()

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.eliminar_plan_venta("123")

        # Assert
        assert mock_db.delete.called
        assert mock_db.commit.called
        assert "message" in result

    def test_eliminar_plan_venta_no_existente_falla(self):
        """Test: Fallar al eliminar plan de venta que no existe"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        service = PlanVentaService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.eliminar_plan_venta("999")

        assert exc_info.value.status_code == 404


class TestPlanVentaServiceContar:
    """Tests para contar planes de venta"""

    def test_contar_planes_venta_exitoso(self):
        """Test: Contar planes de venta exitosamente"""
        # Arrange
        mock_db = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 5
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.contar_planes_venta()

        # Assert
        assert result == 5

    def test_contar_planes_venta_con_filtro_zona(self):
        """Test: Contar planes de venta filtrados por zona"""
        # Arrange
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter().count.return_value = 2
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.contar_planes_venta(zona_asignada="Perú")

        # Assert
        assert result == 2

    def test_contar_planes_venta_cuando_no_hay_ninguno(self):
        """Test: Contar planes de venta cuando no hay ninguno"""
        # Arrange
        mock_db = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 0
        mock_db.query.return_value = mock_query

        service = PlanVentaService(db=mock_db)

        # Act
        result = service.contar_planes_venta()

        # Assert
        assert result == 0
