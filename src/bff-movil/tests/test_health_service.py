from unittest.mock import Mock, patch
from services.health_service import HealthService


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_ok(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock all services to return healthy
    for mock_service in [mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert len(result["services"]) == 4
    assert result["services"]["autenticacion"]["status"] == "healthy"
    assert result["services"]["clientes"]["status"] == "healthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_with_details(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock services with detailed health information
    mock_autenticacion_instance = Mock()
    mock_autenticacion_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
    mock_autenticacion.return_value = mock_autenticacion_instance
    
    mock_clientes_instance = Mock()
    mock_clientes_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
    mock_clientes.return_value = mock_clientes_instance
    
    mock_ordenes_commands_instance = Mock()
    mock_ordenes_commands_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
    mock_ordenes_commands.return_value = mock_ordenes_commands_instance
    
    mock_ordenes_queries_instance = Mock()
    mock_ordenes_queries_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
    mock_ordenes_queries.return_value = mock_ordenes_queries_instance
    
    service = HealthService()
    result = service.check_overall_health(include_details=True)
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert "details" in result["services"]["autenticacion"]
    assert "details" in result["services"]["clientes"]
    assert "details" in result["services"]["ordenes_commands"]
    assert "details" in result["services"]["ordenes_queries"]
    assert result["services"]["autenticacion"]["details"]["version"] == "1.0"


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_without_details(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock all services to return healthy
    for mock_service in [mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy", "version": "1.0"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health(include_details=False)
    
    assert result["status"] == "healthy"
    assert "services" in result
    assert "details" not in result["services"]["autenticacion"]
    assert "details" not in result["services"]["clientes"]
    assert "details" not in result["services"]["ordenes_commands"]
    assert "details" not in result["services"]["ordenes_queries"]


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_degraded_when_one_service_fails(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock autenticacion to fail
    mock_autenticacion_instance = Mock()
    mock_autenticacion_instance.health_check.side_effect = Exception("Connection failed")
    mock_autenticacion.return_value = mock_autenticacion_instance
    
    # Mock other services as healthy
    for mock_service in [mock_ordenes_queries, mock_ordenes_commands, mock_clientes]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert "error" in result["services"]["autenticacion"]
    assert result["services"]["autenticacion"]["error"] == "Connection failed"
    assert result["services"]["clientes"]["status"] == "healthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_degraded_when_multiple_services_fail(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock autenticacion and clientes to fail
    mock_autenticacion_instance = Mock()
    mock_autenticacion_instance.health_check.side_effect = Exception("Autenticacion error")
    mock_autenticacion.return_value = mock_autenticacion_instance
    
    mock_clientes_instance = Mock()
    mock_clientes_instance.health_check.side_effect = Exception("Clientes error")
    mock_clientes.return_value = mock_clientes_instance
    
    # Mock other services as healthy
    for mock_service in [mock_ordenes_queries, mock_ordenes_commands]:
        mock_instance = Mock()
        mock_instance.health_check.return_value = {"status": "healthy"}
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert result["services"]["clientes"]["status"] == "unhealthy"
    assert result["services"]["ordenes_commands"]["status"] == "healthy"
    assert result["services"]["ordenes_queries"]["status"] == "healthy"


@patch('services.health_service.AutenticacionService')
@patch('services.health_service.ClientesService')
@patch('services.health_service.OrdenesCommandsService')
@patch('services.health_service.OrdenesQueriesService')
def test_overall_health_all_services_fail(mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion):
    # Mock all services to fail
    for mock_service in [mock_ordenes_queries, mock_ordenes_commands, mock_clientes, mock_autenticacion]:
        mock_instance = Mock()
        mock_instance.health_check.side_effect = Exception("Service unavailable")
        mock_service.return_value = mock_instance
    
    service = HealthService()
    result = service.check_overall_health()
    
    assert result["status"] == "degraded"
    assert result["services"]["autenticacion"]["status"] == "unhealthy"
    assert result["services"]["clientes"]["status"] == "unhealthy"
    assert result["services"]["ordenes_commands"]["status"] == "unhealthy"
    assert result["services"]["ordenes_queries"]["status"] == "unhealthy"
