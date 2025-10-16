
import pytest
from models.producto import Producto
from services.productos_service import ProductosService
from fastapi import HTTPException


class TestProductosService:

    def test_get_productos_disponibles_vacio(self, test_db):
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 0
        assert len(productos) == 0
    
    def test_get_productos_disponibles_con_datos(self, test_db):
        producto = Producto(
            nombre="Producto Test",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
        )
        test_db.add(producto)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 1
        assert len(productos) == 1
        assert productos[0].nombre == "Producto Test"
    
    def test_get_productos_solo_disponibles(self, test_db):
        producto1 = Producto(
            nombre="Disponible",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
        )
        producto2 = Producto(
            nombre="No Disponible",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=False,
            unidad_medida="UNIDAD"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles()
        
        assert total == 1
        assert productos[0].nombre == "Disponible"
    
    def test_get_productos_solo_con_stock(self, test_db):
        producto1 = Producto(
            nombre="Con Stock",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
        )
        producto2 = Producto(
            nombre="Sin Stock",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=0,
            disponible=True,
            unidad_medida="UNIDAD"
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
        producto1 = Producto(
            nombre="Medicamento",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
        )
        producto2 = Producto(
            nombre="Insumo",
            categoria="INSUMOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = service.get_productos_disponibles(categoria="MEDICAMENTOS")
        
        assert total == 1
        assert productos[0].categoria == "MEDICAMENTOS"
    
    def test_crear_producto_exitoso(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        producto = service.crear_producto(producto_data)
        
        assert producto.nombre == producto_ejemplo["nombre"]
        assert producto.stock_disponible == producto_ejemplo["stock_disponible"]
        assert producto.id is not None
    
    def test_crear_producto_sku_duplicado(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        
        service.crear_producto(producto_data)
        
        with pytest.raises(HTTPException) as exc_info:
            service.crear_producto(producto_data)
        
        assert exc_info.value.status_code == 400
        assert "SKU" in str(exc_info.value.detail)
    
    def test_get_producto_by_id_existe(self, test_db):
        producto = Producto(
            nombre="Producto Test",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD"
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
    
    def test_actualizar_producto_exitoso(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate, ProductoUpdate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        producto = service.crear_producto(producto_data)
        
        update_data = ProductoUpdate(nombre="Nombre Actualizado", precio_unitario=25.00)
        producto_actualizado = service.actualizar_producto(producto.id, update_data)
        
        assert producto_actualizado.nombre == "Nombre Actualizado"
        assert float(producto_actualizado.precio_unitario) == 25.00
        assert producto_actualizado.stock_disponible == producto_ejemplo["stock_disponible"]
    
    def test_eliminar_producto_soft_delete(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        producto = service.crear_producto(producto_data)
        
        resultado = service.eliminar_producto(producto.id)
        
        assert resultado is True
        
        producto_eliminado = service.get_producto_by_id(producto.id)
        assert producto_eliminado.disponible is False
    
    def test_actualizar_stock_incrementar(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        producto = service.crear_producto(producto_data)
        stock_inicial = producto.stock_disponible
        
        producto_actualizado = service.actualizar_stock(producto.id, 50)
        
        assert producto_actualizado.stock_disponible == stock_inicial + 50
    
    def test_actualizar_stock_decrementar(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        producto = service.crear_producto(producto_data)
        stock_inicial = producto.stock_disponible
        
        producto_actualizado = service.actualizar_stock(producto.id, -30)
        
        assert producto_actualizado.stock_disponible == stock_inicial - 30
    
    def test_actualizar_stock_insuficiente(self, test_db, producto_ejemplo):
        from schemas.producto_schema import ProductoCreate
        
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo)
        producto = service.crear_producto(producto_data)
        
        with pytest.raises(HTTPException) as exc_info:
            service.actualizar_stock(producto.id, -200)
        
        assert exc_info.value.status_code == 400
        assert "stock" in str(exc_info.value.detail).lower()

