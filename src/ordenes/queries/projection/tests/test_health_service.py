from services.health_service import HealthService


def test_check_database_health_ok(healthy_deps):
    service = HealthService(db=healthy_deps["db"])
    result = service.check_database_health()
    assert result == {"status": "healthy", "service": "database"}


def test_overall_health_ok(healthy_deps):
    service = HealthService(db=healthy_deps["db"])
    result = service.check_overall_health()
    assert result["status"] == "healthy"
    assert result["database"]["status"] == "healthy"


def test_database_unhealthy(failing_db_deps):
    service = HealthService(db=failing_db_deps["db"])
    result = service.check_database_health()
    assert result["status"] == "unhealthy"
    assert result["service"] == "database"
    assert "error" in result


def test_overall_unhealthy_when_any_fails(failing_db_deps):
    service = HealthService(db=failing_db_deps["db"])
    result = service.check_overall_health()
    assert result["status"] == "unhealthy"
