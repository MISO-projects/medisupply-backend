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
        assert "stock_disponible" not in data 
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
            "nombre": "", 
            "precio_unitario": -10, 
        }
        response = client.post("/api/productos/", json=producto_invalido)
        assert response.status_code == 422

class TestInicializarProductosEndpoint:
    
    async def test_seed_productos_primera_vez(self, client):
        """Test: Inicializar productos por primera vez"""
        client.delete("/api/productos/init/clean")
        
        response = client.post("/api/productos/init/seed")
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["productos_creados"] == 13 


class TestObtenerProductosPorIdsEndpoint:
    """Tests para el endpoint POST /api/productos/by-ids"""
    
    def test_obtener_productos_por_ids_exitoso(self, client, producto_ejemplo):
        """Test: Obtener múltiples productos por IDs"""
        # Crear productos
        producto1 = producto_ejemplo.copy()
        producto1["nombre"] = "Producto 1"
        producto1["sku"] = "TEST-PROD-1"
        response1 = client.post("/api/productos/", json=producto1)
        producto_id_1 = response1.json()["id"]
        
        producto2 = producto_ejemplo.copy()
        producto2["nombre"] = "Producto 2"
        producto2["sku"] = "TEST-PROD-2"
        response2 = client.post("/api/productos/", json=producto2)
        producto_id_2 = response2.json()["id"]
        
        # Obtener productos por IDs
        response = client.post("/api/productos/by-ids", json={"ids": [producto_id_1, producto_id_2]})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert {p["id"] for p in data} == {producto_id_1, producto_id_2}
        nombres = {p["nombre"] for p in data}
        assert "Producto 1" in nombres
        assert "Producto 2" in nombres
    
    def test_obtener_productos_por_ids_lista_vacia(self, client):
        """Test: Obtener productos con lista vacía de IDs"""
        response = client.post("/api/productos/by-ids", json={"ids": []})
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_obtener_productos_por_ids_parcial(self, client, producto_ejemplo):
        """Test: Obtener productos cuando algunos IDs no existen"""
        # Crear un producto
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id_existente = response_create.json()["id"]
        
        # Intentar obtener con ID existente y uno que no existe
        producto_id_inexistente = "id-que-no-existe"
        response = client.post("/api/productos/by-ids", json={"ids": [producto_id_existente, producto_id_inexistente]})
        
        assert response.status_code == 200
        data = response.json()
        # Solo debe retornar el producto que existe
        assert len(data) == 1
        assert data[0]["id"] == producto_id_existente
    
    def test_obtener_productos_por_ids_todos_inexistentes(self, client):
        """Test: Obtener productos cuando ningún ID existe"""
        response = client.post("/api/productos/by-ids", json={"ids": ["id-1", "id-2"]})
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_obtener_productos_por_ids_duplicados(self, client, producto_ejemplo):
        """Test: Obtener productos con IDs duplicados en la lista"""
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Solicitar el mismo ID dos veces
        response = client.post("/api/productos/by-ids", json={"ids": [producto_id, producto_id]})
        
        assert response.status_code == 200
        data = response.json()
        # Debe retornar solo una instancia del producto
        assert len(data) == 1
        assert data[0]["id"] == producto_id
    
    def test_obtener_productos_por_ids_formato_invalido(self, client):
        """Test: Error con formato de request inválido"""
        # Sin el campo 'ids'
        response = client.post("/api/productos/by-ids", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_obtener_productos_por_ids_campo_invalido(self, client):
        """Test: Error cuando 'ids' no es una lista"""
        response = client.post("/api/productos/by-ids", json={"ids": "no-es-una-lista"})
        
        assert response.status_code == 422  # Validation error


class TestIntegracionCompleta:
    
    async def test_flujo_completo_producto(self, client, producto_ejemplo_dict):
        """Test: Flujo completo de creación, consulta, actualización y eliminación"""
        response_create = client.post("/api/productos/", json=producto_ejemplo_dict)
        assert response_create.status_code == 201
        producto_id = response_create.json()["id"]
        
        response_get = client.get(f"/api/productos/{producto_id}")
        assert response_get.status_code == 200
        assert response_get.json()["nombre"] == producto_ejemplo_dict["nombre"]
        
        response_update = client.put(
            f"/api/productos/{producto_id}",
            json={"precio_unitario": 18.00}
        )
        assert response_update.status_code == 200
        assert float(response_update.json()["precio_unitario"]) == 18.00
        
        response_list = client.get("/api/productos/creados") 
        assert response_list.status_code == 200
        assert response_list.json()["total"] == 1
        
        response_delete = client.delete(f"/api/productos/{producto_id}")
        assert response_delete.status_code == 204
        
        response_final = client.get(f"/api/productos/{producto_id}")
        response_final = client.get(f"/api/productos/{producto_id}")
        assert response_final.status_code == 200 
        assert response_final.json()["disponible"] is False 