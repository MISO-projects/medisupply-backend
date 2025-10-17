"""
Tests para el servicio de inicialización de productos
"""
import pytest
from models.producto import Producto
from services.init_service import InitService


class TestInitService:
    """Tests para InitService"""
    
    def test_inicializar_productos_primera_vez(self, test_db):
        """Test: Inicializar productos por primera vez"""
        service = InitService(test_db)
        resultado = service.inicializar_productos()
        
        assert resultado["status"] == "success"
        assert resultado["productos_creados"] == 13
        assert resultado["estadisticas"]["total"] == 13
        assert resultado["estadisticas"]["disponibles"] == 12
        assert resultado["estadisticas"]["con_stock"] == 11
        
        # Verificar categorías (el total debe ser 13 productos)
        medicamentos = resultado["estadisticas"]["por_categoria"]["MEDICAMENTOS"]
        insumos = resultado["estadisticas"]["por_categoria"]["INSUMOS"]
        equipos = resultado["estadisticas"]["por_categoria"]["EQUIPOS"]
        
        assert medicamentos + insumos + equipos == 13
        assert medicamentos >= 4
        assert insumos >= 3
        assert equipos >= 3
    
    def test_inicializar_productos_ya_existen(self, test_db):
        """Test: Inicializar cuando ya existen productos"""
        service = InitService(test_db)
        
        # Primera inicialización
        service.inicializar_productos()
        
        # Segunda inicialización
        resultado = service.inicializar_productos()
        
        assert resultado["status"] == "skipped"
        assert resultado["productos_creados"] == 0
        assert "Ya existen" in resultado["message"]
        assert resultado["productos_existentes"] == 13
    
    def test_inicializar_productos_con_force(self, test_db):
        """Test: Forzar reinicialización eliminando productos existentes"""
        # Crear un producto manual
        producto_manual = Producto(
            nombre="Producto Manual",
            categoria="MEDICAMENTOS",
            precio_unitario=10.00,
            stock_disponible=50,
            disponible=True,
            unidad_medida="UNIDAD",
            sku="MANUAL-001"
        )
        test_db.add(producto_manual)
        test_db.commit()
        
        # Verificar que existe
        count_antes = test_db.query(Producto).count()
        assert count_antes == 1
        
        # Forzar inicialización
        service = InitService(test_db)
        resultado = service.inicializar_productos(force=True)
        
        assert resultado["status"] == "success"
        assert resultado["productos_creados"] == 13
        assert resultado["estadisticas"]["total"] == 13
        
        # El producto manual debe haber sido eliminado
        producto_encontrado = test_db.query(Producto).filter(
            Producto.sku == "MANUAL-001"
        ).first()
        assert producto_encontrado is None
    
    def test_get_productos_ejemplo(self, test_db):
        """Test: Verificar que get_productos_ejemplo retorna 13 productos"""
        service = InitService(test_db)
        productos = service.get_productos_ejemplo()
        
        assert len(productos) == 13
        
        # Verificar que tiene productos de cada categoría
        categorias = [p.categoria for p in productos]
        assert "MEDICAMENTOS" in categorias
        assert "INSUMOS" in categorias
        assert "EQUIPOS" in categorias
        
        # Verificar que todos tienen los campos requeridos
        for producto in productos:
            assert producto.nombre
            assert producto.categoria
            assert producto.precio_unitario > 0
            assert producto.unidad_medida
            assert producto.sku
    
    def test_limpiar_productos_exitoso(self, test_db):
        """Test: Limpiar todos los productos"""
        service = InitService(test_db)
        
        # Crear productos
        service.inicializar_productos()
        
        # Verificar que existen
        count_antes = test_db.query(Producto).count()
        assert count_antes == 13
        
        # Limpiar
        resultado = service.limpiar_productos()
        
        assert resultado["status"] == "success"
        assert resultado["productos_eliminados"] == 13
        
        # Verificar que no quedan productos
        count_despues = test_db.query(Producto).count()
        assert count_despues == 0
    
    def test_limpiar_productos_vacio(self, test_db):
        """Test: Limpiar cuando no hay productos"""
        service = InitService(test_db)
        resultado = service.limpiar_productos()
        
        assert resultado["status"] == "skipped"
        assert resultado["productos_eliminados"] == 0
        assert "No hay productos" in resultado["message"]
    
    def test_productos_ejemplo_tienen_datos_validos(self, test_db):
        """Test: Verificar que los productos de ejemplo tienen datos válidos"""
        service = InitService(test_db)
        productos = service.get_productos_ejemplo()
        
        for producto in productos:
            # Validar nombre
            assert len(producto.nombre) > 0
            assert len(producto.nombre) <= 255
            
            # Validar precio
            assert producto.precio_unitario > 0
            
            # Validar stock (puede ser 0 o positivo)
            assert producto.stock_disponible >= 0
            
            # Validar categoría
            assert producto.categoria in ["MEDICAMENTOS", "INSUMOS", "EQUIPOS"]
            
            # Validar unidad de medida
            assert producto.unidad_medida in ["CAJA", "UNIDAD", "LITRO", "DOSIS"]
            
            # Validar SKU único
            sku_list = [p.sku for p in productos]
            assert sku_list.count(producto.sku) == 1
    
    def test_productos_ejemplo_incluyen_casos_especiales(self, test_db):
        """Test: Verificar que hay productos para casos especiales de testing"""
        service = InitService(test_db)
        productos = service.get_productos_ejemplo()
        
        # Debe haber al menos un producto sin stock
        productos_sin_stock = [p for p in productos if p.stock_disponible == 0]
        assert len(productos_sin_stock) > 0
        
        # Debe haber al menos un producto no disponible
        productos_no_disponibles = [p for p in productos if not p.disponible]
        assert len(productos_no_disponibles) > 0
    
    def test_estadisticas_correctas_despues_init(self, test_db):
        """Test: Verificar que las estadísticas son correctas después de inicializar"""
        service = InitService(test_db)
        resultado = service.inicializar_productos()
        
        # Contar manualmente en la base de datos
        total_db = test_db.query(Producto).count()
        disponibles_db = test_db.query(Producto).filter(Producto.disponible == True).count()
        con_stock_db = test_db.query(Producto).filter(
            Producto.disponible == True,
            Producto.stock_disponible > 0
        ).count()
        
        medicamentos_db = test_db.query(Producto).filter(
            Producto.categoria == "MEDICAMENTOS"
        ).count()
        insumos_db = test_db.query(Producto).filter(
            Producto.categoria == "INSUMOS"
        ).count()
        equipos_db = test_db.query(Producto).filter(
            Producto.categoria == "EQUIPOS"
        ).count()
        
        # Comparar con estadísticas reportadas
        assert resultado["estadisticas"]["total"] == total_db
        assert resultado["estadisticas"]["disponibles"] == disponibles_db
        assert resultado["estadisticas"]["con_stock"] == con_stock_db
        assert resultado["estadisticas"]["por_categoria"]["MEDICAMENTOS"] == medicamentos_db
        assert resultado["estadisticas"]["por_categoria"]["INSUMOS"] == insumos_db
        assert resultado["estadisticas"]["por_categoria"]["EQUIPOS"] == equipos_db

