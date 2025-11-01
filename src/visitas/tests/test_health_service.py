from services.health_service import HealthService


def test_check_database_health_ok(healthy_deps):
    service = HealthService(db=healthy_deps["db"], redis_client=healthy_deps["redis_client"])
    result = service.check_database_health()
    assert result == {"status": "healthy", "service": "database"}


def test_check_cache_health_ok(healthy_deps):
    service = HealthService(db=healthy_deps["db"], redis_client=healthy_deps["redis_client"])
    result = service.check_cache_health()
    assert result == {"status": "healthy", "service": "cache"}


def test_overall_health_ok(healthy_deps):
    service = HealthService(db=healthy_deps["db"], redis_client=healthy_deps["redis_client"])
    result = service.check_overall_health()
    assert result["status"] == "healthy"
    assert result["database"]["status"] == "healthy"
    assert result["cache"]["status"] == "healthy"


def test_database_unhealthy(failing_db_deps):
    service = HealthService(db=failing_db_deps["db"], redis_client=failing_db_deps["redis_client"])
    result = service.check_database_health()
    assert result["status"] == "unhealthy"
    assert result["service"] == "database"
    assert "error" in result


def test_cache_unhealthy(failing_cache_deps):
    service = HealthService(db=failing_cache_deps["db"], redis_client=failing_cache_deps["redis_client"])
    result = service.check_cache_health()
    assert result["status"] == "unhealthy"
    assert result["service"] == "cache"
    assert "error" in result


def test_overall_unhealthy_when_any_fails(failing_db_deps):
    service = HealthService(db=failing_db_deps["db"], redis_client=failing_db_deps["redis_client"])
    result = service.check_overall_health()
    assert result["status"] == "unhealthy"


