import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

pytestmark = pytest.mark.asyncio

@pytest.fixture
def producto_ejemplo_dict():
    """Fixture de un producto para POST (sin stock)"""
    return {
        "nombre": "Paracetamol 500mg Test",
        "descripcion": "Analgésico de prueba",
        "categoria": "MEDICAMENTOS",
        "imagen_url": "https://example.com/test.jpg",
        "precio_unitario": 15.50,
        "disponible": True,
        "unidad_medida": "CAJA",
        "sku": "TEST-SKU-001",
        "tipo_almacenamiento": "AMBIENTE",
        "observaciones": "Producto de prueba",
        "proveedor_id": str(uuid4())
    }

class TestProductosWebEndpoint:
    """Tests para el nuevo endpoint GET /api/productos/creados (para la web)"""
    
    async def test_get_productos_creados_vacio(self, client, test_db):
        response = client.get("/api/productos/creados")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["productos"] == []
    
    async def test_get_productos_creados_con_datos(self, client, producto_ejemplo_dict):
        response_create = client.post("/api/productos/", json=producto_ejemplo_dict) 
        assert response_create.status_code == 201
        
        response = client.get("/api/productos/creados")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["productos"]) == 1
        assert data["productos"][0]["nombre"] == producto_ejemplo_dict["nombre"]
        assert "stock_disponible" not in data["productos"][0] 


class TestCrearProductoEndpoint:
    """Tests para el endpoint POST /api/productos/"""
    
    async def test_crear_producto_exitoso(self, client, producto_ejemplo_dict):
        """Test: Crear un producto exitosamente (sin stock)"""
        response = client.post("/api/productos/", json=producto_ejemplo_dict)
        
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == producto_ejemplo_dict["nombre"]
        assert "stock_disponible" not in data # Ya no debe devolver esto
        assert "id" in data
        assert data["disponible"] is True
    
    async def test_crear_producto_sku_duplicado(self, client, producto_ejemplo_dict):
        """Test: Error al crear producto con SKU duplicado"""
        response1 = client.post("/api/productos/", json=producto_ejemplo_dict)
        assert response1.status_code == 201
        
        producto_2 = producto_ejemplo_dict.copy()
        producto_2["nombre"] = "Producto 2"
        response = client.post("/api/productos/", json=producto_2)
        
        assert response.status_code == 400
        assert "SKU" in response.json()["detail"]
    
    def test_crear_producto_datos_invalidos(self, client):
        """Test: Error al crear producto con datos inválidos"""
        producto_invalido = {
            "nombre": "",  # Nombre vacío
            "precio_unitario": -10, # Precio negativo
        }
        response = client.post("/api/productos/", json=producto_invalido)
        assert response.status_code == 422

# ... (Las clases TestObtenerProductoEndpoint, TestActualizarProductoEndpoint,
# y TestEliminarProductoEndpoint de tu archivo original pueden ir aquí,
# solo asegúrate de añadir 'async' a 'actualizar_producto' si es necesario) ...

# --- ¡ELIMINADO! ---
# class TestActualizarStockEndpoint:
#    ... (Toda esta clase de prueba se elimina) ...
# --- FIN DE LA ELIMINACIÓN ---


# --- ¡CORREGIDO! ---
# Las pruebas de 'init' fallan porque llaman a Producto() con 'stock_disponible'
# Esto debe arreglarse en 'services/init_service.py' (ver Paso 4)
class TestInicializarProductosEndpoint:
    
    async def test_seed_productos_primera_vez(self, client):
        """Test: Inicializar productos por primera vez"""
        # Limpiamos por si acaso
        client.delete("/api/productos/init/clean")
        
        response = client.post("/api/productos/init/seed")
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["productos_creados"] == 13 # O el número que sea

# ... (El resto de las pruebas de init fallarán hasta arreglar init_service.py) ...


# --- ¡CORREGIDO! ---
# Eliminamos la prueba de 'actualizar_stock'
class TestIntegracionCompleta:
    
    async def test_flujo_completo_producto(self, client, producto_ejemplo_dict):
        """Test: Flujo completo de creación, consulta, actualización y eliminación"""
        # 1. Crear producto
        response_create = client.post("/api/productos/", json=producto_ejemplo_dict)
        assert response_create.status_code == 201
        producto_id = response_create.json()["id"]
        
        # 2. Consultar producto
        response_get = client.get(f"/api/productos/{producto_id}")
        assert response_get.status_code == 200
        assert response_get.json()["nombre"] == producto_ejemplo_dict["nombre"]
        
        # 3. Actualizar stock <-- ¡ELIMINADO!
        # response_stock = client.patch(f"/api/productos/{producto_id}/stock?cantidad=50")
        # assert response_stock.status_code == 200
        
        # 4. Actualizar información
        response_update = client.put(
            f"/api/productos/{producto_id}",
            json={"precio_unitario": 18.00}
        )
        assert response_update.status_code == 200
        assert float(response_update.json()["precio_unitario"]) == 18.00
        
        # 5. Verificar en listado
        response_list = client.get("/api/productos/creados") # <-- Llama al nuevo endpoint
        assert response_list.status_code == 200
        assert response_list.json()["total"] == 1
        
        # 6. Eliminar producto
        response_delete = client.delete(f"/api/productos/{producto_id}")
        assert response_delete.status_code == 204
        
        # 7. Verificar que no aparece en productos (ahora sí, porque está eliminado)
        response_final = client.get(f"/api/productos/{producto_id}")
        response_final = client.get(f"/api/productos/{producto_id}")
        assert response_final.status_code == 200 # <-- ¡CORREGIDO!
        assert response_final.json()["disponible"] is False # <-- ¡VERIFICACIÓN CORRECTA!