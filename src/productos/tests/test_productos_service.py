import pytest
from models.producto import Producto
from services.productos_service import ProductosService
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from schemas.producto_schema import ProductoCreate, ProductoUpdate

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
pytestmark = pytest.mark.asyncio

class TestProductosService:

    async def test_get_productos_creados_web_vacio(self, test_db):
        service = ProductosService(test_db)
        productos, total = await service.get_productos_creados_web()
        
        assert total == 0
        assert len(productos) == 0
    
    async def test_get_productos_creados_web_con_datos(self, test_db):
        producto = Producto(
            nombre="Producto Test",
            descripcion="Descripción test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=uuid4(),
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto)
        test_db.commit()
        
        service = ProductosService(test_db)
        productos, total = await service.get_productos_creados_web()
        
        assert total == 1
        assert len(productos) == 1
        assert productos[0].nombre == "Producto Test"
    async def test_get_productos_por_categoria_web(self, test_db):
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Medicamento",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
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
        productos, total = await service.get_productos_creados_web(categoria="MEDICAMENTOS")
        
        assert total == 1
        assert productos[0].categoria == "MEDICAMENTOS"
    
    async def test_crear_producto_exitoso(self, test_db, producto_ejemplo_dict):
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo_dict)
        
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo_dict["proveedor_id"], "nombre": "Proveedor Test"}
            
            producto_dict = await service.crear_producto(producto_data)
            
            assert producto_dict["nombre"] == producto_ejemplo_dict["nombre"]
            assert producto_dict["id"] is not None
            assert producto_dict["proveedor_nombre"] == "Proveedor Test"
    
    async def test_crear_producto_sku_duplicado(self, test_db, producto_ejemplo_dict):
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo_dict)
        
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo_dict["proveedor_id"], "nombre": "Proveedor Test"}
            
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
        
        assert resultado.id == str(producto.id)
        assert resultado.nombre == "Producto Test"
    
    def test_get_producto_by_id_no_existe(self, test_db):
        service = ProductosService(test_db)
        
        with pytest.raises(HTTPException) as exc_info:
            service.get_producto_by_id("id-inexistente")
        
        assert exc_info.value.status_code == 404
    
    async def test_actualizar_producto_exitoso(self, test_db, producto_ejemplo_dict):
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo_dict)
        
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo_dict["proveedor_id"], "nombre": "Proveedor Test"}
            producto_dict = await service.crear_producto(producto_data)
        
        update_data = ProductoUpdate(nombre="Nombre Actualizado", precio_unitario=25.00)
        producto_actualizado = service.actualizar_producto(producto_dict["id"], update_data)
        
        assert producto_actualizado.nombre == "Nombre Actualizado"
        assert float(producto_actualizado.precio_unitario) == 25.00
 
    async def test_eliminar_producto_soft_delete(self, test_db, producto_ejemplo_dict):
        service = ProductosService(test_db)
        producto_data = ProductoCreate(**producto_ejemplo_dict)
        
        with patch.object(service, '_verificar_proveedor_activo', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"id": producto_ejemplo_dict["proveedor_id"], "nombre": "Proveedor Test"}
            producto_dict = await service.crear_producto(producto_data)
        
        resultado = service.eliminar_producto(producto_dict["id"])
        
        assert resultado is True
        
        producto_eliminado = service.get_producto_by_id(producto_dict["id"])
        assert producto_eliminado.disponible is False
    
    
    

    
    def test_get_productos_by_ids_exitoso(self, test_db):
        """Test: Obtener múltiples productos por IDs"""
        proveedor_id = uuid4()
        
        producto1 = Producto(
            nombre="Producto 1",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        producto2 = Producto(
            nombre="Producto 2",
            descripcion="Test",
            categoria="INSUMOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=15.00,
            disponible=True,
            unidad_medida="CAJA",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        test_db.refresh(producto1)
        test_db.refresh(producto2)
        
        service = ProductosService(test_db)
        resultados = service.get_productos_by_ids([producto1.id, producto2.id])
        
        assert len(resultados) == 2
        ids_resultados = {p.id for p in resultados}
        assert ids_resultados == {producto1.id, producto2.id}
        nombres = {p.nombre for p in resultados}
        assert "Producto 1" in nombres
        assert "Producto 2" in nombres
    
    def test_get_productos_by_ids_lista_vacia(self, test_db):
        """Test: Obtener productos con lista vacía de IDs"""
        service = ProductosService(test_db)
        resultados = service.get_productos_by_ids([])
        
        assert resultados == []
    
    def test_get_productos_by_ids_parcial(self, test_db):
        """Test: Obtener productos cuando algunos IDs no existen"""
        proveedor_id = uuid4()
        producto = Producto(
            nombre="Producto Existente",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto)
        test_db.commit()
        test_db.refresh(producto)
        
        service = ProductosService(test_db)
        resultados = service.get_productos_by_ids([producto.id, "id-inexistente"])
        
        assert len(resultados) == 1
        assert resultados[0].id == producto.id
        assert resultados[0].nombre == "Producto Existente"
    
    def test_get_productos_by_ids_todos_inexistentes(self, test_db):
        """Test: Obtener productos cuando ningún ID existe"""
        service = ProductosService(test_db)
        resultados = service.get_productos_by_ids(["id-1", "id-2"])
        
        assert resultados == []
    
    def test_get_productos_by_ids_duplicados(self, test_db):
        """Test: Obtener productos con IDs duplicados en la lista"""
        proveedor_id = uuid4()
        producto = Producto(
            nombre="Producto Único",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto)
        test_db.commit()
        test_db.refresh(producto)
        
        service = ProductosService(test_db)
        resultados = service.get_productos_by_ids([producto.id, producto.id])
        
        # SQLAlchemy puede retornar duplicados o puede deduplicar dependiendo de la query
        # Pero al menos debe haber uno
        assert len(resultados) >= 1
        assert any(p.id == producto.id for p in resultados)

    def test_get_producto_ids_by_filters_text_search_nombre(self, test_db):
        """Test: Buscar productos por text_search en nombre"""
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Paracetamol 500mg",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-001"
        )
        producto2 = Producto(
            nombre="Ibuprofeno 400mg",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=15.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-002"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        test_db.refresh(producto1)
        test_db.refresh(producto2)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="Paracetamol")
        
        assert len(resultado) == 1
        assert str(producto1.id) in resultado
        assert str(producto2.id) not in resultado

    def test_get_producto_ids_by_filters_text_search_sku(self, test_db):
        """Test: Buscar productos por text_search en SKU"""
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Producto Test",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="PRD-20250101-ABC12"
        )
        producto2 = Producto(
            nombre="Otro Producto",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=15.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="PRD-20250101-XYZ99"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        test_db.refresh(producto1)
        test_db.refresh(producto2)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="ABC12")
        
        assert len(resultado) == 1
        assert str(producto1.id) in resultado
        assert str(producto2.id) not in resultado

    def test_get_producto_ids_by_filters_text_search_nombre_or_sku(self, test_db):
        """Test: Buscar productos por text_search que coincida con nombre o SKU"""
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Paracetamol",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-001"
        )
        producto2 = Producto(
            nombre="Ibuprofeno",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=15.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="PARA-001"  # SKU contiene "PARA" que también está en "Paracetamol"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        test_db.refresh(producto1)
        test_db.refresh(producto2)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="PARA")
        
        # Debe encontrar ambos: uno por nombre (Paracetamol) y otro por SKU (PARA-001)
        assert len(resultado) == 2
        assert str(producto1.id) in resultado
        assert str(producto2.id) in resultado

    def test_get_producto_ids_by_filters_text_search_with_categoria(self, test_db):
        """Test: Buscar productos por text_search y categoria"""
        proveedor_id = uuid4()
        producto1 = Producto(
            nombre="Paracetamol",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-001"
        )
        producto2 = Producto(
            nombre="Paracetamol",
            descripcion="Test",
            categoria="INSUMOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=15.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-002"
        )
        test_db.add(producto1)
        test_db.add(producto2)
        test_db.commit()
        test_db.refresh(producto1)
        test_db.refresh(producto2)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="Paracetamol", categoria="MEDICAMENTOS")
        
        assert len(resultado) == 1
        assert str(producto1.id) in resultado
        assert str(producto2.id) not in resultado

    def test_get_producto_ids_by_filters_text_search_no_results(self, test_db):
        """Test: Buscar productos por text_search sin resultados"""
        proveedor_id = uuid4()
        producto = Producto(
            nombre="Paracetamol",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-001"
        )
        test_db.add(producto)
        test_db.commit()
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="Inexistente")
        
        assert len(resultado) == 0

    def test_get_producto_ids_by_filters_text_search_case_insensitive(self, test_db):
        """Test: text_search es case-insensitive"""
        proveedor_id = uuid4()
        producto = Producto(
            nombre="Paracetamol",
            descripcion="Test",
            categoria="MEDICAMENTOS",
            imagen_url="http://test.com/img.jpg",
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test",
            sku="SKU-001"
        )
        test_db.add(producto)
        test_db.commit()
        test_db.refresh(producto)
        
        service = ProductosService(test_db)
        resultado = service.get_producto_ids_by_filters(text_search="paracetamol")
        
        assert len(resultado) == 1
        assert str(producto.id) in resultado

