from services.health_service import HealthService


def test_overall_health_ok():
    service = HealthService()
    result = service.check_overall_health()
    assert result["status"] == "healthy"
