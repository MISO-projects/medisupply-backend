import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from services.order_service import get_order_service
import jwt


@pytest.fixture
def mock_order_service():
    """Mock order service"""
    service = Mock()
    service.get_orders_by_client.return_value = []
    service.count_orders_by_client.return_value = 0
    return service


@pytest.fixture
def client(mock_order_service):
    """Test client with mocked dependencies"""
    app.dependency_overrides[get_order_service] = lambda: mock_order_service
    test_client = TestClient(app)
    yield test_client
    # Clean up
    app.dependency_overrides.clear()


def create_test_token(client_id: str, role: str = "client") -> str:
    """Helper to create test JWT tokens"""
    payload = {
        "id_client": client_id,
        "role": role,
        "email": "test@example.com"
    }
    return jwt.encode(payload, "secret", algorithm="HS256")


class TestGetOrdersByClientEndpoint:
    """Tests for GET /orders/client-orders endpoint"""

    def test_get_client_orders_success(self, client, mock_order_service):
        """Test successful retrieval of client orders"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        mock_orders = [
            {
                "id": "order-1",
                "numero_orden": "ORD-001",
                "id_cliente": client_id,
                "estado": "PENDING"
            },
            {
                "id": "order-2",
                "numero_orden": "ORD-002",
                "id_cliente": client_id,
                "estado": "COMPLETED"
            }
        ]
        
        mock_order_service.get_orders_by_client.return_value = mock_orders
        mock_order_service.count_orders_by_client.return_value = 2
        
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert len(data["data"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_get_client_orders_with_pagination(self, client, mock_order_service):
        """Test getting client orders with custom pagination"""
        client_id = "client-123"
        token = create_test_token(client_id)
        page = 2
        page_size = 10
        
        mock_orders = [{"id": f"order-{i}"} for i in range(10)]
        mock_order_service.get_orders_by_client.return_value = mock_orders
        mock_order_service.count_orders_by_client.return_value = 25
        
        response = client.get(
            f"/orders/client-orders?page={page}&page_size={page_size}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == page
        assert data["page_size"] == page_size
        assert data["total"] == 25
        assert data["total_pages"] == 3
        
        # Verify service was called with correct skip/limit
        mock_order_service.get_orders_by_client.assert_called_once_with(
            id_cliente=client_id,
            skip=10,  # (page - 1) * page_size
            limit=10
        )

    def test_get_client_orders_empty_result(self, client, mock_order_service):
        """Test getting client orders when client has no orders"""
        client_id = "client-456"
        token = create_test_token(client_id)
        
        mock_order_service.get_orders_by_client.return_value = []
        mock_order_service.count_orders_by_client.return_value = 0
        
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["total_pages"] == 0

    def test_get_client_orders_no_token(self, client):
        """Test getting client orders without authorization token"""
        response = client.get("/orders/client-orders")
        
        assert response.status_code == 401
        assert "Token de autorización requerido" in response.json()["detail"]

    def test_get_client_orders_invalid_token_format(self, client):
        """Test getting client orders with invalid token format"""
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": "InvalidFormat token123"}
        )
        
        assert response.status_code == 401
        assert "Formato de token inválido" in response.json()["detail"]

    def test_get_client_orders_malformed_token(self, client):
        """Test getting client orders with malformed JWT token"""
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": "Bearer malformed.token.here"}
        )
        
        assert response.status_code == 401

    def test_get_client_orders_wrong_role(self, client):
        """Test getting client orders with non-client role"""
        token = create_test_token("user-123", role="admin")
        
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "Solo usuarios con rol 'client'" in response.json()["detail"]

    def test_get_client_orders_no_client_id_in_token(self, client):
        """Test getting client orders when token doesn't contain id_client"""
        payload = {
            "role": "client",
            "email": "test@example.com"
            # Missing id_client
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "Token no contiene id_client" in response.json()["detail"]

    def test_get_client_orders_invalid_page_number(self, client):
        """Test getting client orders with invalid page number"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        response = client.get(
            "/orders/client-orders?page=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error

    def test_get_client_orders_page_size_exceeds_max(self, client):
        """Test getting client orders with page_size exceeding maximum"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        response = client.get(
            "/orders/client-orders?page_size=101",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error

    def test_get_client_orders_service_error(self, client, mock_order_service):
        """Test getting client orders when service raises error"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        mock_order_service.get_orders_by_client.side_effect = HTTPException(
            status_code=500,
            detail="Error interno al obtener órdenes del cliente."
        )
        
        response = client.get(
            "/orders/client-orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 500
        assert "Error interno" in response.json()["detail"]


class TestGetClientIdFromAuth:
    """Tests for get_client_id_from_auth dependency"""

    def test_extract_client_id_success(self, client):
        """Test successful extraction of client_id from token"""
        from router.order_router import get_client_id_from_auth
        
        client_id = "client-123"
        token = create_test_token(client_id)
        
        result = get_client_id_from_auth(authorization=f"Bearer {token}")
        
        assert result == client_id

    def test_extract_client_id_no_authorization(self, client):
        """Test extraction when no authorization header is provided"""
        from router.order_router import get_client_id_from_auth
        
        with pytest.raises(HTTPException) as exc_info:
            get_client_id_from_auth(authorization=None)
        
        assert exc_info.value.status_code == 401

    def test_extract_client_id_invalid_format(self, client):
        """Test extraction with invalid authorization format"""
        from router.order_router import get_client_id_from_auth
        
        with pytest.raises(HTTPException) as exc_info:
            get_client_id_from_auth(authorization="Basic token123")
        
        assert exc_info.value.status_code == 401

    def test_extract_client_id_wrong_role(self, client):
        """Test extraction when user has wrong role"""
        from router.order_router import get_client_id_from_auth
        
        token = create_test_token("user-123", role="vendor")
        
        with pytest.raises(HTTPException) as exc_info:
            get_client_id_from_auth(authorization=f"Bearer {token}")
        
        assert exc_info.value.status_code == 403


class TestPaginationCalculations:
    """Tests for pagination calculations"""

    def test_pagination_total_pages_calculation(self, client, mock_order_service):
        """Test correct calculation of total_pages"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        test_cases = [
            (0, 20, 0),    # No orders
            (1, 20, 1),    # One order
            (20, 20, 1),   # Exactly one page
            (21, 20, 2),   # One order into second page
            (40, 20, 2),   # Exactly two pages
            (100, 20, 5),  # Multiple pages
            (99, 10, 10),  # Edge case
        ]
        
        for total, page_size, expected_pages in test_cases:
            mock_order_service.get_orders_by_client.return_value = []
            mock_order_service.count_orders_by_client.return_value = total
            
            response = client.get(
                f"/orders/client-orders?page_size={page_size}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_pages"] == expected_pages, \
                f"Failed for total={total}, page_size={page_size}: expected {expected_pages}, got {data['total_pages']}"

    def test_pagination_skip_calculation(self, client, mock_order_service):
        """Test correct calculation of skip value"""
        client_id = "client-123"
        token = create_test_token(client_id)
        
        test_cases = [
            (1, 20, 0),    # First page
            (2, 20, 20),   # Second page
            (3, 20, 40),   # Third page
            (1, 10, 0),    # First page, smaller size
            (5, 10, 40),   # Fifth page, smaller size
        ]
        
        for page, page_size, expected_skip in test_cases:
            mock_order_service.get_orders_by_client.return_value = []
            mock_order_service.count_orders_by_client.return_value = 100
            mock_order_service.get_orders_by_client.reset_mock()  # Reset call history
            
            response = client.get(
                f"/orders/client-orders?page={page}&page_size={page_size}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            
            # Verify service was called with correct skip
            call_args = mock_order_service.get_orders_by_client.call_args
            assert call_args.kwargs['skip'] == expected_skip, \
                f"Failed for page={page}, page_size={page_size}: expected skip={expected_skip}"

