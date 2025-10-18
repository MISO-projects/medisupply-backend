
import pytest
from models.producto import Producto
from services.productos_service import ProductosService
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from uuid import uuid4


class TestProductosService:

    def test_get_productos_disponibles_vacio(self, test_db):
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 0
        assert len(productos) == 0
    
    def test_get_productos_disponibles_con_datos(self, test_db):
        producto = Producto(
            nombre="Producto Test",
            descripcion="Descripción test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=uuid4(),
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 1
        assert len(productos) == 1
        assert productos[0].nombre == "Producto Test"
    
    def test_get_productos_solo_disponibles(self, test_db):
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Disponible",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        producto2 = Producto(
            nombre="No Disponible",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=False,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 1
        assert productos[0].nombre == "Disponible"
    
    def test_get_productos_solo_con_stock(self, test_db):
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Con Stock",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        producto2 = Producto(
            nombre="Sin Stock",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=0,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles(solo_con_stock=True)
        
        assert total == 1
        assert productos[0].nombre == "Con Stock"
        
        productos, total = service.get_productos_disponibles(solo_con_stock=False)
        assert total == 2
    
    def test_get_productos_por_categoria(self, test_db):
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Medicamento",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        producto2 = Producto(
            nombre="Insumo",
            descripcion="Test",
            categoria="INSUMOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles(categoria="MEDICAMENTOS")
        
        assert total == 1
        assert productos[0].categoria == "MEDICAMENTOS"
    
    @pytest.mark.asyncio
    async def test_crear_producto_exitoso(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            
            producto = await service.crear_producto(producto_data)
            
            assert producto.nombre == producto_ejemplo["nombre"]
            assert producto.stock_disponible == producto_ejemplo["stock_disponible"]
            assert producto.id is not None
            assert producto.proveedor_nombre == "Proveedor Test"
    
    @pytest.mark.asyncio
    async def test_crear_producto_sku_duplicado(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            
            await service.crear_producto(producto_data)
            
            with pytest.raises(HTTPException) as exc_info:
                await service.crear_producto(producto_data)
            
            assert exc_info.value.status_code == 400
            assert "SKU" in str(exc_info.value.detail)
    
    def test_get_producto_by_id_existe(self, test_db):
        producto = Producto(
            nombre="Producto Test",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=uuid4(),
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto)
        test_db.commit()
        test_db.refresh(producto)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_by_id(producto.id)
        
        assert resultado.id == producto.id
        assert resultado.nombre == "Producto Test"
    
    def test_get_producto_by_id_no_existe(self, test_db):
        service = ProductosService(test_db)
        
        with pytest.raises(HTTPException) as exc_info:
            service.get_producto_by_id("id-inexistente")
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_actualizar_producto_exitoso(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate, ProductoUpdate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            producto = await service.crear_producto(producto_data)
        
        update_data = ProductoUpdate(nombre="Nombre Actualizado", precio_unitario=25.00)
        producto_actualizado = service.actualizar_producto(producto.id, update_data)
        
        assert producto_actualizado.nombre == "Nombre Actualizado"
        assert float(producto_actualizado.precio_unitario) == 25.00
        assert producto_actualizado.stock_disponible == producto_ejemplo["stock_disponible"]
    
    @pytest.mark.asyncio
    async def test_eliminar_producto_soft_delete(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            producto = await service.crear_producto(producto_data)
        
        resultado = service.eliminar_producto(producto.id)
        
        assert resultado is True
        
        producto_eliminado = service.get_producto_by_id(producto.id)
        assert producto_eliminado.disponible is False
    
    @pytest.mark.asyncio
    async def test_actualizar_stock_incrementar(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            producto = await service.crear_producto(producto_data)
        
        stock_inicial = producto.stock_disponible
        
        producto_actualizado = service.actualizar_stock(producto.id, 50)
        
        assert producto_actualizado.stock_disponible == stock_inicial + 50
    
    @pytest.mark.asyncio
    async def test_actualizar_stock_decrementar(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            producto = await service.crear_producto(producto_data)
        
        stock_inicial = producto.stock_disponible
        
        producto_actualizado = service.actualizar_stock(producto.id, -30)
        
        assert producto_actualizado.stock_disponible == stock_inicial - 30
    
    @pytest.mark.asyncio
    async def test_actualizar_stock_insuficiente(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        # Mock the provider verification
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo["proveedor_id"], "nombre": "Proveedor Test"}
            producto = await service.crear_producto(producto_data)
        
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_stock(producto.id, -200)
        
        assert exc_info.value.status_code == 400
        assert "stock" in str(exc_info.value.detail).lower()

