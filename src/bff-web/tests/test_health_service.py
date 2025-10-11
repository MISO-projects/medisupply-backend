from unittest.mock import Mock, patch
from services.health_service import HealthService


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_ok(mock_ventas, mock_reportes, mock_proveedores, mock_productos, 
                          mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                          mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock all services to return healthy
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert len(result["services"]) == 11
    assert result["services"]["auditoria"]["status"] == "healthy"
    assert result["services"]["autenticacion"]["status"] == "healthy"
    assert result["services"]["clientes"]["status"] == "healthy"
    assert result["services"]["inventario"]["status"] == "healthy"
    assert result["services"]["logistica"]["status"] == "healthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"
    assert result["services"]["productos"]["status"] == "healthy"
    assert result["services"]["proveedores"]["status"] == "healthy"
    assert result["services"]["reportes"]["status"] == "healthy"
    assert result["services"]["ventas"]["status"] == "healthy"


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_with_details(mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                                     mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                                     mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock all services with detailed health information
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health(include_details=True)
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert "details" in result["services"]["auditoria"]
    assert "details" in result["services"]["autenticacion"]
    assert "details" in result["services"]["clientes"]
    assert "details" in result["services"]["inventario"]
    assert "details" in result["services"]["logistica"]
    assert "details" in result["services"]["ordenes_commands"]
    assert "details" in result["services"]["ordenes_queries"]
    assert "details" in result["services"]["productos"]
    assert "details" in result["services"]["proveedores"]
    assert "details" in result["services"]["reportes"]
    assert "details" in result["services"]["ventas"]
    assert result["services"]["auditoria"]["details"]["version"] == "1.0"


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_without_details(mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                                       mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                                       mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock all services to return healthy
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health(include_details=False)
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert "details" not in result["services"]["auditoria"]
    assert "details" not in result["services"]["autenticacion"]
    assert "details" not in result["services"]["clientes"]
    assert "details" not in result["services"]["inventario"]
    assert "details" not in result["services"]["logistica"]
    assert "details" not in result["services"]["ordenes_commands"]
    assert "details" not in result["services"]["ordenes_queries"]
    assert "details" not in result["services"]["productos"]
    assert "details" not in result["services"]["proveedores"]
    assert "details" not in result["services"]["reportes"]
    assert "details" not in result["services"]["ventas"]


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_degraded_when_one_service_fails(mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                                                       mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                                                       mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock autenticacion to fail
    mock_autenticacion_instance = Mock()
    mock_autenticacion_instance.health_check.side_effect = Exception("Connection failed")
    mock_autenticacion.return_value = mock_autenticacion_instance
    
    # Mock other services as healthy
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert "error" in result["services"]["autenticacion"]
    assert result["services"]["autenticacion"]["error"] == "Connection failed"
    assert result["services"]["auditoria"]["status"] == "healthy"
    assert result["services"]["clientes"]["status"] == "healthy"
    assert result["services"]["inventario"]["status"] == "healthy"
    assert result["services"]["logistica"]["status"] == "healthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"
    assert result["services"]["productos"]["status"] == "healthy"
    assert result["services"]["proveedores"]["status"] == "healthy"
    assert result["services"]["reportes"]["status"] == "healthy"
    assert result["services"]["ventas"]["status"] == "healthy"


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_degraded_when_multiple_services_fail(mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                                                             mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                                                             mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock autenticacion and productos to fail
    mock_autenticacion_instance = Mock()
    mock_autenticacion_instance.health_check.side_effect = Exception("Autenticacion error")
    mock_autenticacion.return_value = mock_autenticacion_instance
    
    mock_productos_instance = Mock()
    mock_productos_instance.health_check.side_effect = Exception("Productos error")
    mock_productos.return_value = mock_productos_instance
    
    # Mock other services as healthy
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, 
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert result["services"]["productos"]["status"] == "unhealthy"
    assert result["services"]["auditoria"]["status"] == "healthy"
    assert result["services"]["clientes"]["status"] == "healthy"
    assert result["services"]["inventario"]["status"] == "healthy"
    assert result["services"]["logistica"]["status"] == "healthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"
    assert result["services"]["proveedores"]["status"] == "healthy"
    assert result["services"]["reportes"]["status"] == "healthy"
    assert result["services"]["ventas"]["status"] == "healthy"


@patch('services.health_service.AuditoriaService')
@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.InventarioService')
@patch('services.health_service.LogisticaService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
@patch('services.health_service.ProductosService')
@patch('services.health_service.ProveedoresService')
@patch('services.health_service.ReportesService')
@patch('services.health_service.VentasService')
def test_overall_health_all_services_fail(mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                                          mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                                          mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria):
    # Mock all services to fail
    for mock_service in [mock_ventas, mock_reportes, mock_proveedores, mock_productos,
                        mock_ordenes_queries, mock_ordenes_commands, mock_logistica,
                        mock_inventario, mock_clientes, mock_autenticacion, mock_auditoria]:
        mock_instance = Mock()
        mock_instance.health_check.side_effect = Exception("Service unavailable")
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["auditoria"]["status"] == "unhealthy"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert result["services"]["clientes"]["status"] == "unhealthy"
    assert result["services"]["inventario"]["status"] == "unhealthy"
    assert result["services"]["logistica"]["status"] == "unhealthy"
    assert result["services"]["ordenes_commands"]["status"] == "unhealthy"
    assert result["services"]["ordenes_queries"]["status"] == "unhealthy"
    assert result["services"]["productos"]["status"] == "unhealthy"
    assert result["services"]["proveedores"]["status"] == "unhealthy"
    assert result["services"]["reportes"]["status"] == "unhealthy"
    assert result["services"]["ventas"]["status"] == "unhealthy"
