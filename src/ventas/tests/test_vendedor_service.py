import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException
from decimal import Decimal

from services.vendedor_service import VendedorService
from schemas.vendedor_schema import CrearVendedorSchema, ActualizarVendedorSchema, ZonaAsignadaEnum
from db.vendedor_model import Vendedor


class TestVendedorServiceCrear:
    """Tests para crear vendedor"""

    def test_crear_vendedor_exitoso(self):
        """Test: Crear vendedor exitosamente"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None  # No existe vendedor con ese email
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        vendedor_data = CrearVendedorSchema(
            nombre="Juan Pérez",
            documento_identidad="12345678",
            email="juan@medisupply.com",
            zona_asignada=ZonaAsignadaEnum.PERU,
            plan_venta="plan-123",
            meta_venta=Decimal("50000.00")
        )

        service = VendedorService(db=mock_db)

        # Act
        result = service.crear_vendedor(vendedor_data)

        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert "nombre" in result
        assert result["nombre"] == "Juan Pérez"

    def test_crear_vendedor_email_duplicado_falla(self):
        """Test: Fallar al crear vendedor con email duplicado"""
        # Arrange
        mock_db = Mock()

        # Simular que ya existe un vendedor con ese email
        vendedor_existente = Mock()
        vendedor_existente.email = "juan@medisupply.com"
        mock_db.query().filter().first.return_value = vendedor_existente

        vendedor_data = CrearVendedorSchema(
            nombre="Juan Pérez",
            documento_identidad="12345678",
            email="juan@medisupply.com",
            zona_asignada=ZonaAsignadaEnum.PERU
        )

        service = VendedorService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.crear_vendedor(vendedor_data)

        assert exc_info.value.status_code == 409
        assert "email" in str(exc_info.value.detail).lower()


class TestVendedorServiceObtener:
    """Tests para obtener vendedor"""

    def test_obtener_vendedor_existente(self):
        """Test: Obtener vendedor que existe"""
        # Arrange
        mock_db = Mock()

        vendedor_mock = Mock()
        vendedor_mock.to_dict.return_value = {
            "id": "123",
            "nombre": "Juan Pérez",
            "email": "juan@medisupply.com",
            "zona_asignada": "Perú"
        }

        mock_db.query().filter().first.return_value = vendedor_mock

        service = VendedorService(db=mock_db)

        # Act
        result = service.obtener_vendedor("123")

        # Assert
        assert result["id"] == "123"
        assert result["nombre"] == "Juan Pérez"

    def test_obtener_vendedor_no_existente_falla(self):
        """Test: Fallar al obtener vendedor que no existe"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        service = VendedorService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.obtener_vendedor("999")

        assert exc_info.value.status_code == 404


class TestVendedorServiceListar:
    """Tests para listar vendedores"""

    def test_listar_vendedores_exitoso(self):
        """Test: Listar vendedores exitosamente"""
        # Arrange
        mock_db = Mock()

        vendedor1 = Mock()
        vendedor1.to_dict.return_value = {"id": "1", "nombre": "Juan"}

        vendedor2 = Mock()
        vendedor2.to_dict.return_value = {"id": "2", "nombre": "María"}

        mock_query = Mock()
        mock_query.order_by().offset().limit().all.return_value = [vendedor1, vendedor2]
        mock_db.query.return_value = mock_query

        service = VendedorService(db=mock_db)

        # Act
        result = service.listar_vendedores(skip=0, limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]["nombre"] == "Juan"
        assert result[1]["nombre"] == "María"

    def test_listar_vendedores_vacio(self):
        """Test: Listar vendedores cuando no hay ninguno"""
        # Arrange
        mock_db = Mock()

        mock_query = Mock()
        mock_query.order_by().offset().limit().all.return_value = []
        mock_db.query.return_value = mock_query

        service = VendedorService(db=mock_db)

        # Act
        result = service.listar_vendedores(skip=0, limit=10)

        # Assert
        assert len(result) == 0


class TestVendedorServiceActualizar:
    """Tests para actualizar vendedor"""

    def test_actualizar_vendedor_exitoso(self):
        """Test: Actualizar vendedor exitosamente"""
        # Arrange
        mock_db = Mock()

        vendedor_mock = Mock()
        vendedor_mock.id = "123"
        vendedor_mock.email = "juan@medisupply.com"
        vendedor_mock.to_dict.return_value = {
            "id": "123",
            "nombre": "Juan Pérez Actualizado",
            "email": "juan@medisupply.com"
        }

        # Primera llamada: buscar el vendedor a actualizar
        # Segunda llamada: verificar si el email ya existe en otro vendedor
        mock_db.query().filter().first.side_effect = [vendedor_mock, None]
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        vendedor_data = ActualizarVendedorSchema(
            nombre="Juan Pérez Actualizado"
        )

        service = VendedorService(db=mock_db)

        # Act
        result = service.actualizar_vendedor("123", vendedor_data)

        # Assert
        assert mock_db.commit.called
        assert result["nombre"] == "Juan Pérez Actualizado"

    def test_actualizar_vendedor_no_existente_falla(self):
        """Test: Fallar al actualizar vendedor que no existe"""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        vendedor_data = ActualizarVendedorSchema(nombre="Nuevo Nombre")

        service = VendedorService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_vendedor("999", vendedor_data)

        assert exc_info.value.status_code == 404

    def test_actualizar_vendedor_email_duplicado_falla(self):
        """Test: Fallar al actualizar con email que ya existe en otro vendedor"""
        # Arrange
        mock_db = Mock()

        vendedor_actual = Mock()
        vendedor_actual.id = "123"
        vendedor_actual.email = "juan@medisupply.com"

        otro_vendedor = Mock()
        otro_vendedor.id = "456"
        otro_vendedor.email = "maria@medisupply.com"

        # Primera llamada: encontrar el vendedor a actualizar
        # Segunda llamada: verificar si el nuevo email ya existe
        mock_db.query().filter().first.side_effect = [vendedor_actual, otro_vendedor]

        vendedor_data = ActualizarVendedorSchema(
            email="maria@medisupply.com"  # Email que ya existe en otro vendedor
        )

        service = VendedorService(db=mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_vendedor("123", vendedor_data)

        assert exc_info.value.status_code == 409


class TestVendedorServiceContar:
    """Tests para contar vendedores"""

    def test_contar_vendedores_exitoso(self):
        """Test: Contar vendedores exitosamente"""
        # Arrange
        mock_db = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 5
        mock_db.query.return_value = mock_query

        service = VendedorService(db=mock_db)

        # Act
        result = service.contar_vendedores()

        # Assert
        assert result == 5

    def test_contar_vendedores_cuando_no_hay_ninguno(self):
        """Test: Contar vendedores cuando no hay ninguno"""
        # Arrange
        mock_db = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 0
        mock_db.query.return_value = mock_query

        service = VendedorService(db=mock_db)

        # Act
        result = service.contar_vendedores()

        # Assert
        assert result == 0
