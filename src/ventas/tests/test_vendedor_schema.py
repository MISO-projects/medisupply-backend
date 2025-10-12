import pytest
from pydantic import ValidationError
from decimal import Decimal

from schemas.vendedor_schema import (
    CrearVendedorSchema,
    ActualizarVendedorSchema,
    ZonaAsignadaEnum
)


class TestCrearVendedorSchema:
    """Tests para el schema de creación de vendedor"""

    def test_crear_vendedor_schema_valido(self):
        """Test: Crear vendedor con todos los datos válidos"""
        data = {
            "nombre": "Juan Pérez García",
            "documento_identidad": "12345678",
            "email": "juan.perez@medisupply.com",
            "zona_asignada": "Perú",
            "plan_venta": "plan-123",
            "meta_venta": 50000.00
        }

        vendedor = CrearVendedorSchema(**data)

        assert vendedor.nombre == "Juan Pérez García"
        assert vendedor.documento_identidad == "12345678"
        assert vendedor.email == "juan.perez@medisupply.com"
        assert vendedor.zona_asignada == ZonaAsignadaEnum.PERU
        assert vendedor.plan_venta == "plan-123"
        assert vendedor.meta_venta == Decimal("50000.00")

    def test_crear_vendedor_schema_sin_campos_opcionales(self):
        """Test: Crear vendedor sin campos opcionales"""
        data = {
            "nombre": "María González",
            "documento_identidad": "87654321",
            "email": "maria@medisupply.com",
            "zona_asignada": "Colombia"
        }

        vendedor = CrearVendedorSchema(**data)

        assert vendedor.nombre == "María González"
        assert vendedor.plan_venta is None
        assert vendedor.meta_venta is None

    def test_crear_vendedor_nombre_vacio_falla(self):
        """Test: Fallar si el nombre está vacío"""
        data = {
            "nombre": "   ",
            "documento_identidad": "12345678",
            "email": "test@medisupply.com",
            "zona_asignada": "Perú"
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearVendedorSchema(**data)

        assert "nombre" in str(exc_info.value)

    def test_crear_vendedor_email_invalido_falla(self):
        """Test: Fallar si el email es inválido"""
        data = {
            "nombre": "Juan Pérez",
            "documento_identidad": "12345678",
            "email": "email-invalido",
            "zona_asignada": "Perú"
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearVendedorSchema(**data)

        assert "email" in str(exc_info.value)

    def test_crear_vendedor_zona_invalida_falla(self):
        """Test: Fallar si la zona no es válida"""
        data = {
            "nombre": "Juan Pérez",
            "documento_identidad": "12345678",
            "email": "juan@medisupply.com",
            "zona_asignada": "Argentina"  # No está en el enum
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearVendedorSchema(**data)

        assert "zona_asignada" in str(exc_info.value)

    def test_crear_vendedor_meta_venta_negativa_falla(self):
        """Test: Fallar si la meta de venta es negativa"""
        data = {
            "nombre": "Juan Pérez",
            "documento_identidad": "12345678",
            "email": "juan@medisupply.com",
            "zona_asignada": "Perú",
            "meta_venta": -1000
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearVendedorSchema(**data)

        assert "meta_venta" in str(exc_info.value)

    def test_crear_vendedor_sin_campos_obligatorios_falla(self):
        """Test: Fallar si faltan campos obligatorios"""
        data = {
            "nombre": "Juan Pérez"
            # Faltan: documento_identidad, email, zona_asignada
        }

        with pytest.raises(ValidationError) as exc_info:
            CrearVendedorSchema(**data)

        errors = str(exc_info.value)
        assert "documento_identidad" in errors
        assert "email" in errors
        assert "zona_asignada" in errors


class TestActualizarVendedorSchema:
    """Tests para el schema de actualización de vendedor"""

    def test_actualizar_vendedor_schema_valido(self):
        """Test: Actualizar vendedor con datos válidos"""
        data = {
            "nombre": "Juan Pérez Actualizado",
            "email": "nuevo@medisupply.com",
            "meta_venta": 75000.00
        }

        vendedor = ActualizarVendedorSchema(**data)

        assert vendedor.nombre == "Juan Pérez Actualizado"
        assert vendedor.email == "nuevo@medisupply.com"
        assert vendedor.meta_venta == Decimal("75000.00")

    def test_actualizar_vendedor_todos_campos_opcionales(self):
        """Test: Todos los campos son opcionales en actualización"""
        data = {}

        vendedor = ActualizarVendedorSchema(**data)

        assert vendedor.nombre is None
        assert vendedor.email is None
        assert vendedor.zona_asignada is None
        assert vendedor.plan_venta is None
        assert vendedor.meta_venta is None

    def test_actualizar_vendedor_nombre_vacio_falla(self):
        """Test: Fallar si el nombre está vacío"""
        data = {
            "nombre": "   "
        }

        with pytest.raises(ValidationError) as exc_info:
            ActualizarVendedorSchema(**data)

        assert "nombre" in str(exc_info.value)

    def test_actualizar_vendedor_email_invalido_falla(self):
        """Test: Fallar si el email es inválido"""
        data = {
            "email": "email-sin-arroba"
        }

        with pytest.raises(ValidationError) as exc_info:
            ActualizarVendedorSchema(**data)

        assert "email" in str(exc_info.value)
