import pytest
from pydantic import ValidationError
import sys
from pathlib import Path

# Add parent directory to path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
    PaisEnum,
    TipoProveedorEnum
)


class TestCrearProveedorSchema:
    """Tests para validación del schema de creación de proveedor"""
    
    def test_schema_valido_peru(self):
        """Test: Schema válido para Perú con RUC de 11 dígitos"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Farmacéutica Nacional S.A.",
            id_tributario="20123456789",
            tipo_proveedor=TipoProveedorEnum.FABRICANTE,
            email="contacto@farmaceutica.com",
            pais=PaisEnum.PERU,
            contacto="Juan Pérez",
            condiciones_entrega="Entrega en 5 días"
        )
        
        # Assert
        assert proveedor.nombre == "Farmacéutica Nacional S.A."
        assert proveedor.id_tributario == "20123456789"
        assert proveedor.pais == PaisEnum.PERU
        
    def test_schema_valido_colombia(self):
        """Test: Schema válido para Colombia con NIT de 9 dígitos"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Farmacia Colombia",
            id_tributario="900123456",
            tipo_proveedor=TipoProveedorEnum.DISTRIBUIDOR,
            email="contacto@colombia.com",
            pais=PaisEnum.COLOMBIA
        )
        
        # Assert
        assert proveedor.id_tributario == "900123456"
        assert proveedor.pais == PaisEnum.COLOMBIA
        
    def test_schema_valido_colombia_10_digitos(self):
        """Test: Schema válido para Colombia con NIT de 10 dígitos"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Farmacia Colombia",
            id_tributario="9001234567",
            tipo_proveedor=TipoProveedorEnum.DISTRIBUIDOR,
            email="contacto@colombia.com",
            pais=PaisEnum.COLOMBIA
        )
        
        # Assert
        assert proveedor.id_tributario == "9001234567"
        
    def test_schema_valido_mexico(self):
        """Test: Schema válido para México con RFC"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Farmacia México",
            id_tributario="ABC123456789",
            tipo_proveedor=TipoProveedorEnum.MAYORISTA,
            email="contacto@mexico.com",
            pais=PaisEnum.MEXICO
        )
        
        # Assert
        assert proveedor.id_tributario == "ABC123456789"
        assert proveedor.pais == PaisEnum.MEXICO
        
    def test_schema_valido_ecuador(self):
        """Test: Schema válido para Ecuador con RUC de 13 dígitos"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Farmacia Ecuador",
            id_tributario="1234567890123",
            tipo_proveedor=TipoProveedorEnum.IMPORTADOR,
            email="contacto@ecuador.com",
            pais=PaisEnum.ECUADOR
        )
        
        # Assert
        assert proveedor.id_tributario == "1234567890123"
        assert proveedor.pais == PaisEnum.ECUADOR
        
    def test_ruc_peru_invalido_longitud(self):
        """Test: Error con RUC de Perú con longitud incorrecta"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="201234567",  # Solo 9 dígitos
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU
            )
        
        assert "RUC debe tener 11 dígitos" in str(exc_info.value)
        
    def test_ruc_peru_invalido_caracteres(self):
        """Test: Error con RUC de Perú con caracteres no numéricos"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="2012345678A",  # Contiene letra
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU
            )
        
        assert "RUC debe tener 11 dígitos" in str(exc_info.value)
        
    def test_nit_colombia_invalido(self):
        """Test: Error con NIT de Colombia con longitud incorrecta"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="12345",  # Solo 5 dígitos
                tipo_proveedor=TipoProveedorEnum.DISTRIBUIDOR,
                email="test@test.com",
                pais=PaisEnum.COLOMBIA
            )
        
        assert "NIT debe tener 9 o 10 dígitos" in str(exc_info.value)
        
    def test_ruc_ecuador_invalido(self):
        """Test: Error con RUC de Ecuador con longitud incorrecta"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="123456789012",  # Solo 12 dígitos
                tipo_proveedor=TipoProveedorEnum.IMPORTADOR,
                email="test@test.com",
                pais=PaisEnum.ECUADOR
            )
        
        assert "RUC debe tener 13 dígitos" in str(exc_info.value)
        
    def test_email_invalido(self):
        """Test: Error con formato de email inválido"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="correo-invalido",  # No es un email válido
                pais=PaisEnum.PERU
            )
        
        assert "email" in str(exc_info.value).lower()
        
    def test_nombre_vacio(self):
        """Test: Error con nombre vacío"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="",
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU
            )
            
    def test_nombre_muy_largo(self):
        """Test: Error con nombre que excede 255 caracteres"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="A" * 256,  # 256 caracteres
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU
            )
            
    def test_contacto_muy_largo(self):
        """Test: Error con contacto que excede 255 caracteres"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU,
                contacto="A" * 256  # 256 caracteres
            )
            
    def test_condiciones_entrega_muy_largo(self):
        """Test: Error con condiciones de entrega que exceden 500 caracteres"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais=PaisEnum.PERU,
                condiciones_entrega="A" * 501  # 501 caracteres
            )
            
    def test_campos_opcionales_none(self):
        """Test: Schema válido con campos opcionales en None"""
        # Arrange & Act
        proveedor = CrearProveedorSchema(
            nombre="Test",
            id_tributario="20123456789",
            tipo_proveedor=TipoProveedorEnum.FABRICANTE,
            email="test@test.com",
            pais=PaisEnum.PERU,
            contacto=None,
            condiciones_entrega=None
        )
        
        # Assert
        assert proveedor.contacto is None
        assert proveedor.condiciones_entrega is None
        
    def test_tipo_proveedor_invalido(self):
        """Test: Error con tipo de proveedor inválido"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="20123456789",
                tipo_proveedor="TipoInvalido",  # No es un valor válido del enum
                email="test@test.com",
                pais=PaisEnum.PERU
            )
            
    def test_pais_invalido(self):
        """Test: Error con país inválido"""
        # Act & Assert
        with pytest.raises(ValidationError):
            CrearProveedorSchema(
                nombre="Test",
                id_tributario="20123456789",
                tipo_proveedor=TipoProveedorEnum.FABRICANTE,
                email="test@test.com",
                pais="Argentina"  # No es un valor válido del enum
            )


class TestActualizarProveedorSchema:
    """Tests para validación del schema de actualización de proveedor"""
    
    def test_actualizacion_parcial_nombre(self):
        """Test: Actualización solo del nombre"""
        # Arrange & Act
        update = ActualizarProveedorSchema(nombre="Nuevo Nombre S.A.C.")
        
        # Assert
        assert update.nombre == "Nuevo Nombre S.A.C."
        assert update.email is None
        assert update.contacto is None
        
    def test_actualizacion_parcial_email(self):
        """Test: Actualización solo del email"""
        # Arrange & Act
        update = ActualizarProveedorSchema(email="nuevo@email.com")
        
        # Assert
        assert update.email == "nuevo@email.com"
        assert update.nombre is None
        
    def test_actualizacion_multiple_campos(self):
        """Test: Actualización de múltiples campos"""
        # Arrange & Act
        update = ActualizarProveedorSchema(
            nombre="Nuevo Nombre",
            email="nuevo@email.com",
            contacto="Nuevo Contacto"
        )
        
        # Assert
        assert update.nombre == "Nuevo Nombre"
        assert update.email == "nuevo@email.com"
        assert update.contacto == "Nuevo Contacto"
        
    def test_actualizacion_email_invalido(self):
        """Test: Error al actualizar con email inválido"""
        # Act & Assert
        with pytest.raises(ValidationError):
            ActualizarProveedorSchema(email="email-invalido")
            
    def test_actualizacion_nombre_muy_largo(self):
        """Test: Error al actualizar con nombre muy largo"""
        # Act & Assert
        with pytest.raises(ValidationError):
            ActualizarProveedorSchema(nombre="A" * 256)
            
    def test_actualizacion_sin_campos(self):
        """Test: Schema válido sin campos (actualización vacía)"""
        # Arrange & Act
        update = ActualizarProveedorSchema()
        
        # Assert
        assert update.nombre is None
        assert update.email is None
        assert update.tipo_proveedor is None
        

class TestEnums:
    """Tests para los enums de país y tipo de proveedor"""
    
    def test_pais_enum_valores(self):
        """Test: Verificar valores del enum PaisEnum"""
        assert PaisEnum.COLOMBIA.value == "Colombia"
        assert PaisEnum.PERU.value == "Perú"
        assert PaisEnum.ECUADOR.value == "Ecuador"
        assert PaisEnum.MEXICO.value == "México"
        
    def test_tipo_proveedor_enum_valores(self):
        """Test: Verificar valores del enum TipoProveedorEnum"""
        assert TipoProveedorEnum.FABRICANTE.value == "Fabricante"
        assert TipoProveedorEnum.DISTRIBUIDOR.value == "Distribuidor"
        assert TipoProveedorEnum.MAYORISTA.value == "Mayorista"
        assert TipoProveedorEnum.IMPORTADOR.value == "Importador"
        assert TipoProveedorEnum.MINORISTA.value == "Minorista"

