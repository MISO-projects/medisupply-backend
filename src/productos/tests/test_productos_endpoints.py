"""
Tests para los endpoints del microservicio de productos
"""
import pytest
from decimal import Decimal


class TestProductosDisponiblesEndpoint:
    """Tests para el endpoint GET /api/productos/disponibles"""
    
    def test_get_productos_disponibles_vacio(self, client):
        """Test: Obtener productos disponibles cuando no hay productos"""
        response = client.get("/api/productos/disponibles")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["productos"] == []
    
    def test_get_productos_disponibles_con_datos(self, client, producto_ejemplo):
        """Test: Obtener productos disponibles con datos"""
        # Crear un producto primero
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Obtener productos disponibles
        response = client.get("/api/productos/disponibles")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["productos"]) == 1
        assert data["productos"][0]["nombre"] == producto_ejemplo["nombre"]
        assert data["productos"][0]["stock_disponible"] == producto_ejemplo["stock_disponible"]
    
    def test_get_productos_solo_con_stock(self, client, producto_ejemplo):
        """Test: Filtrar solo productos con stock disponible"""
        # Crear producto con stock
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Crear producto sin stock
        producto_sin_stock = producto_ejemplo.copy()
        producto_sin_stock["nombre"] = "Producto sin stock"
        producto_sin_stock["sku"] = "TEST-SIN-STOCK"
        producto_sin_stock["stock_disponible"] = 0
        client.post("/api/productos/", json=producto_sin_stock)
        
        # Obtener solo productos con stock
        response = client.get("/api/productos/disponibles?solo_con_stock=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["productos"][0]["stock_disponible"] > 0
    
    def test_get_productos_incluir_sin_stock(self, client, producto_ejemplo):
        """Test: Incluir productos sin stock"""
        # Crear producto con stock
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Crear producto sin stock
        producto_sin_stock = producto_ejemplo.copy()
        producto_sin_stock["nombre"] = "Producto sin stock"
        producto_sin_stock["sku"] = "TEST-SIN-STOCK"
        producto_sin_stock["stock_disponible"] = 0
        client.post("/api/productos/", json=producto_sin_stock)
        
        # Obtener todos los productos
        response = client.get("/api/productos/disponibles?solo_con_stock=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
    
    def test_get_productos_filtrar_por_categoria(self, client, producto_ejemplo):
        """Test: Filtrar productos por categoría"""
        # Crear producto en MEDICAMENTOS
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Crear producto en INSUMOS
        producto_insumo = producto_ejemplo.copy()
        producto_insumo["nombre"] = "Guantes"
        producto_insumo["categoria"] = "INSUMOS"
        producto_insumo["sku"] = "TEST-GUANTES"
        client.post("/api/productos/", json=producto_insumo)
        
        # Filtrar por MEDICAMENTOS
        response = client.get("/api/productos/disponibles?categoria=MEDICAMENTOS")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["productos"][0]["categoria"] == "MEDICAMENTOS"
    
    def test_get_productos_paginacion(self, client, producto_ejemplo):
        """Test: Paginación de productos"""
        # Crear 5 productos
        for i in range(5):
            producto = producto_ejemplo.copy()
            producto["nombre"] = f"Producto {i}"
            producto["sku"] = f"TEST-PROD-{i}"
            client.post("/api/productos/", json=producto)
        
        # Obtener primeros 2
        response = client.get("/api/productos/disponibles?skip=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["productos"]) == 2
        
        # Obtener siguientes 2
        response = client.get("/api/productos/disponibles?skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["productos"]) == 2


class TestCrearProductoEndpoint:
    """Tests para el endpoint POST /api/productos/"""
    
    def test_crear_producto_exitoso(self, client, producto_ejemplo):
        """Test: Crear un producto exitosamente"""
        response = client.post("/api/productos/", json=producto_ejemplo)
        
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == producto_ejemplo["nombre"]
        assert data["stock_disponible"] == producto_ejemplo["stock_disponible"]
        assert "id" in data
        assert data["disponible"] is True
    
    def test_crear_producto_sku_duplicado(self, client, producto_ejemplo):
        """Test: Error al crear producto con SKU duplicado"""
        # Crear primer producto
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Intentar crear producto con mismo SKU
        response = client.post("/api/productos/", json=producto_ejemplo)
        
        assert response.status_code == 400
        assert "SKU" in response.json()["detail"]
    
    def test_crear_producto_sin_sku(self, client, producto_ejemplo):
        """Test: Crear producto sin SKU (opcional)"""
        producto_sin_sku = producto_ejemplo.copy()
        del producto_sin_sku["sku"]
        
        response = client.post("/api/productos/", json=producto_sin_sku)
        
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == producto_ejemplo["nombre"]
    
    def test_crear_producto_datos_invalidos(self, client):
        """Test: Error al crear producto con datos inválidos"""
        producto_invalido = {
            "nombre": "",  # Nombre vacío
            "precio_unitario": -10,  # Precio negativo
            "stock_disponible": -5  # Stock negativo
        }
        
        response = client.post("/api/productos/", json=producto_invalido)
        
        assert response.status_code == 422  # Validation error


class TestObtenerProductoEndpoint:
    """Tests para el endpoint GET /api/productos/{producto_id}"""
    
    def test_obtener_producto_exitoso(self, client, producto_ejemplo):
        """Test: Obtener un producto por ID"""
        # Crear producto
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Obtener producto
        response = client.get(f"/api/productos/{producto_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == producto_id
        assert data["nombre"] == producto_ejemplo["nombre"]
    
    def test_obtener_producto_no_existe(self, client):
        """Test: Error al obtener producto que no existe"""
        response = client.get("/api/productos/id-inexistente")
        
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]


class TestActualizarProductoEndpoint:
    """Tests para el endpoint PUT /api/productos/{producto_id}"""
    
    def test_actualizar_producto_exitoso(self, client, producto_ejemplo):
        """Test: Actualizar un producto exitosamente"""
        # Crear producto
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Actualizar producto
        actualizacion = {
            "nombre": "Nombre Actualizado",
            "precio_unitario": 20.00
        }
        response = client.put(f"/api/productos/{producto_id}", json=actualizacion)
        
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Nombre Actualizado"
        assert float(data["precio_unitario"]) == 20.00
    
    def test_actualizar_producto_no_existe(self, client):
        """Test: Error al actualizar producto que no existe"""
        actualizacion = {"nombre": "Nuevo Nombre"}
        response = client.put("/api/productos/id-inexistente", json=actualizacion)
        
        assert response.status_code == 404


class TestEliminarProductoEndpoint:
    """Tests para el endpoint DELETE /api/productos/{producto_id}"""
    
    def test_eliminar_producto_exitoso(self, client, producto_ejemplo):
        """Test: Eliminar un producto (soft delete)"""
        # Crear producto
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Eliminar producto
        response = client.delete(f"/api/productos/{producto_id}")
        
        assert response.status_code == 204
        
        # Verificar que el producto está marcado como no disponible
        response_get = client.get(f"/api/productos/{producto_id}")
        assert response_get.json()["disponible"] is False
    
    def test_eliminar_producto_no_existe(self, client):
        """Test: Error al eliminar producto que no existe"""
        response = client.delete("/api/productos/id-inexistente")
        
        assert response.status_code == 404


class TestActualizarStockEndpoint:
    """Tests para el endpoint PATCH /api/productos/{producto_id}/stock"""
    
    def test_incrementar_stock(self, client, producto_ejemplo):
        """Test: Incrementar el stock de un producto"""
        # Crear producto con stock inicial de 100
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Incrementar stock
        response = client.patch(f"/api/productos/{producto_id}/stock?cantidad=50")
        
        assert response.status_code == 200
        data = response.json()
        assert data["stock_disponible"] == 150
    
    def test_decrementar_stock(self, client, producto_ejemplo):
        """Test: Decrementar el stock de un producto"""
        # Crear producto con stock inicial de 100
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Decrementar stock
        response = client.patch(f"/api/productos/{producto_id}/stock?cantidad=-30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["stock_disponible"] == 70
    
    def test_decrementar_stock_insuficiente(self, client, producto_ejemplo):
        """Test: Error al decrementar más stock del disponible"""
        # Crear producto con stock inicial de 100
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        producto_id = response_create.json()["id"]
        
        # Intentar decrementar más del stock disponible
        response = client.patch(f"/api/productos/{producto_id}/stock?cantidad=-150")
        
        assert response.status_code == 400
        assert "stock" in response.json()["detail"].lower()


class TestInicializarProductosEndpoint:
    """Tests para el endpoint POST /api/productos/init/seed"""
    
    def test_seed_productos_primera_vez(self, client):
        """Test: Inicializar productos por primera vez"""
        response = client.post("/api/productos/init/seed")
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["productos_creados"] == 13
        assert data["estadisticas"]["total"] == 13
        assert data["estadisticas"]["por_categoria"]["MEDICAMENTOS"] > 0
        assert data["estadisticas"]["por_categoria"]["INSUMOS"] > 0
        assert data["estadisticas"]["por_categoria"]["EQUIPOS"] > 0
    
    def test_seed_productos_ya_existen(self, client):
        """Test: Intentar inicializar cuando ya existen productos"""
        # Primera inicialización
        client.post("/api/productos/init/seed")
        
        # Segunda inicialización
        response = client.post("/api/productos/init/seed")
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "skipped"
        assert data["productos_creados"] == 0
        assert "Ya existen" in data["message"]
    
    def test_seed_productos_con_force(self, client, producto_ejemplo):
        """Test: Forzar reinicialización de productos"""
        # Crear un producto manual
        client.post("/api/productos/", json=producto_ejemplo)
        
        # Forzar seed
        response = client.post("/api/productos/init/seed?force=true")
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["productos_creados"] == 13
        # El producto manual debe haber sido eliminado
        assert data["estadisticas"]["total"] == 13


class TestLimpiarProductosEndpoint:
    """Tests para el endpoint DELETE /api/productos/init/clean"""
    
    def test_limpiar_productos_exitoso(self, client):
        """Test: Limpiar todos los productos"""
        # Crear productos
        client.post("/api/productos/init/seed")
        
        # Limpiar
        response = client.delete("/api/productos/init/clean")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["productos_eliminados"] == 13
    
    def test_limpiar_productos_vacio(self, client):
        """Test: Limpiar cuando no hay productos"""
        response = client.delete("/api/productos/init/clean")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["productos_eliminados"] == 0


class TestIntegracionCompleta:
    """Tests de integración completa del flujo de productos"""
    
    def test_flujo_completo_producto(self, client, producto_ejemplo):
        """Test: Flujo completo de creación, consulta, actualización y eliminación"""
        # 1. Crear producto
        response_create = client.post("/api/productos/", json=producto_ejemplo)
        assert response_create.status_code == 201
        producto_id = response_create.json()["id"]
        
        # 2. Consultar producto
        response_get = client.get(f"/api/productos/{producto_id}")
        assert response_get.status_code == 200
        assert response_get.json()["nombre"] == producto_ejemplo["nombre"]
        
        # 3. Actualizar stock
        response_stock = client.patch(f"/api/productos/{producto_id}/stock?cantidad=50")
        assert response_stock.status_code == 200
        assert response_stock.json()["stock_disponible"] == 150
        
        # 4. Actualizar información
        response_update = client.put(
            f"/api/productos/{producto_id}",
            json={"precio_unitario": 18.00}
        )
        assert response_update.status_code == 200
        assert float(response_update.json()["precio_unitario"]) == 18.00
        
        # 5. Verificar en listado
        response_list = client.get("/api/productos/disponibles")
        assert response_list.status_code == 200
        assert response_list.json()["total"] == 1
        
        # 6. Eliminar producto
        response_delete = client.delete(f"/api/productos/{producto_id}")
        assert response_delete.status_code == 204
        
        # 7. Verificar que no aparece en productos disponibles con stock
        response_final = client.get("/api/productos/disponibles")
        assert response_final.json()["total"] == 0
    
    def test_flujo_seed_y_consulta(self, client):
        """Test: Flujo de seed y consulta de productos"""
        # 1. Inicializar productos
        response_seed = client.post("/api/productos/init/seed")
        assert response_seed.status_code == 201
        assert response_seed.json()["productos_creados"] == 13
        
        # 2. Consultar todos los productos
        response_all = client.get("/api/productos/disponibles?solo_con_stock=false")
        assert response_all.status_code == 200
        assert response_all.json()["total"] == 12  # 12 disponibles (1 no disponible)
        
        # 3. Consultar solo con stock
        response_stock = client.get("/api/productos/disponibles?solo_con_stock=true")
        assert response_stock.status_code == 200
        assert response_stock.json()["total"] == 11  # 11 con stock (1 sin stock)
        
        # 4. Filtrar por categoría
        response_med = client.get("/api/productos/disponibles?categoria=MEDICAMENTOS")
        assert response_med.status_code == 200
        medicamentos = response_med.json()["total"]
        
        response_ins = client.get("/api/productos/disponibles?categoria=INSUMOS")
        assert response_ins.status_code == 200
        insumos = response_ins.json()["total"]
        
        response_equ = client.get("/api/productos/disponibles?categoria=EQUIPOS")
        assert response_equ.status_code == 200
        equipos = response_equ.json()["total"]
        
        # Verificar que las sumas coinciden (sin contar el no disponible)
        assert medicamentos + insumos + equipos == 11
        
        # 5. Limpiar todo
        response_clean = client.delete("/api/productos/init/clean")
        assert response_clean.status_code == 200
        assert response_clean.json()["productos_eliminados"] == 13

