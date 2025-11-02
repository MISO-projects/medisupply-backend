"""
Simple Integration Test for Order Creation with Stock Decrease

This test verifies the complete flow:
1. Order handler receives an order command
2. Order handler calls inventario service to decrease stock
3. Stock is properly decreased in the inventario database

The test runs inside the order-handler container and uses HTTP calls
to verify the integration, avoiding complex model imports.

Run with:
    docker-compose -f docker-compose.test.yml up -d
    docker-compose -f docker-compose.test.yml exec order-handler-test pytest tests/integration/test_order_stock_integration.py -v
    docker-compose -f docker-compose.test.yml down
"""
import pytest
import httpx
import uuid
import base64
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any
import os


# Service URLs (internal Docker network)
ORDER_HANDLER_URL = "http://localhost:3000"
INVENTARIO_SERVICE_URL = "http://inventario-test:3000/api/inventario/"

# Database connection (from environment variables)
def get_db_url():
    user = os.getenv("POSTGRES_USER", "test_user")
    password = os.getenv("POSTGRES_PASSWORD", "test_password")
    host = os.getenv("POSTGRES_HOST", "postgres-test")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "test_medisupply")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def db_engine():
    """Create a database engine for direct DB queries"""
    engine = create_engine(get_db_url())
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for each test"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def sample_product_id():
    """Generate a unique product ID for testing"""
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
async def setup_inventory_stock(db_session, sample_product_id):
    """
    Setup initial inventory stock via the inventario service API.
    This is the proper way to create test data - through the service interface.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create two batches of inventory
        lote1_data = {
            "producto_id": sample_product_id,
            "lote": "LOTE-TEST-001",
            "fecha_vencimiento": (datetime.now() + timedelta(days=30)).date().isoformat(),
            "cantidad": 100,
            "estado": "DISPONIBLE",
            "ubicacion": "ALMACEN-TEST-A",
            "temperatura_requerida": "25.0",
            "condiciones_especiales": None,
            "observaciones": "Test batch 1"
        }
        
        lote2_data = {
            "producto_id": sample_product_id,
            "lote": "LOTE-TEST-002",
            "fecha_vencimiento": (datetime.now() + timedelta(days=60)).date().isoformat(),
            "cantidad": 50,
            "estado": "DISPONIBLE",
            "ubicacion": "ALMACEN-TEST-B",
            "temperatura_requerida": "25.0",
            "condiciones_especiales": None,
            "observaciones": "Test batch 2"
        }
        
        # Create inventory records via API
        response1 = await client.post(
            INVENTARIO_SERVICE_URL,
            json=lote1_data,
            timeout=30.0
        )
        response2 = await client.post(
            INVENTARIO_SERVICE_URL,
            json=lote2_data,
            timeout=30.0
        )
        
        assert response1.status_code == 201, f"Failed to create lote1: {response1.text}"
        assert response2.status_code == 201, f"Failed to create lote2: {response2.text}"
        
        lote1_id = response1.json()["id"]
        lote2_id = response2.json()["id"]
        
        yield {
            "producto_id": sample_product_id,
            "total_stock": 150,
            "lote1_id": lote1_id,
            "lote2_id": lote2_id
        }
        
        # Cleanup: Delete inventory records directly from DB
        try:
            db_session.execute(
                text("DELETE FROM inventario WHERE producto_id = :producto_id"),
                {"producto_id": sample_product_id}
            )
            db_session.commit()
        except Exception as e:
            print(f"Cleanup warning: {e}")
            db_session.rollback()


def create_pubsub_message(data: dict) -> dict:
    """Helper to create a Pub/Sub formatted message"""
    message_json = json.dumps(data)
    message_bytes = message_json.encode("utf-8")
    encoded_data = base64.b64encode(message_bytes).decode("utf-8")
    
    return {
        "message": {
            "data": encoded_data,
            "attributes": {},
            "messageId": f"test-msg-{uuid.uuid4()}",
            "publishTime": datetime.utcnow().isoformat() + "Z"
        }
    }


class TestOrderStockIntegration:
    """Integration tests for order creation with stock decrease"""

    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Verify all services are healthy before running tests"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test order handler health
            handler_response = await client.get(f"{ORDER_HANDLER_URL}/health")
            assert handler_response.status_code == 200
            assert handler_response.json()["status"] == "healthy"
            
            # Test inventario health
            inventario_response = await client.get("http://inventario-test:3000/health")
            assert inventario_response.status_code == 200
            assert inventario_response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_order_creation_decreases_stock_successfully(
        self,
        db_session,
        setup_inventory_stock,
        sample_product_id
    ):
        """
        Test that creating an order successfully decreases stock in inventario.
        
        Flow:
        1. Initial stock: 150 units (100 in LOTE-TEST-001, 50 in LOTE-TEST-002)
        2. Create order for 80 units via handler
        3. Verify order created in handler database
        4. Verify stock decreased to 70 units in inventario database
        5. Verify FIFO/FEFO logic (should consume from LOTE-TEST-001 first)
        """
        initial_stock = setup_inventory_stock["total_stock"]  # 150
        
        # Prepare order data
        order_id = str(uuid.uuid4())
        order_data = {
            "id": order_id,
            "numero_orden": f"ORD-{uuid.uuid4().hex[:8].upper()}",
            "estado": "PENDIENTE",
            "id_cliente": str(uuid.uuid4()),
            "id_vendedor": str(uuid.uuid4()),
            "creado_por": str(uuid.uuid4()),
            "observaciones": "Integration test order",
            "detalles": [
                {
                    "id_producto": sample_product_id,
                    "cantidad": 80,  # Request 80 units
                    "precio_unitario": 100.0,
                    "observaciones": "Test product"
                }
            ]
        }
        
        # Create Pub/Sub formatted message
        pubsub_message = create_pubsub_message(order_data)
        
        # Send order command to handler
        async with httpx.AsyncClient(timeout=30.0) as client:
            handler_response = await client.post(
                f"{ORDER_HANDLER_URL}/",
                json=pubsub_message,
                timeout=30.0
            )
            
            # Verify handler response
            assert handler_response.status_code == 200, \
                f"Handler returned {handler_response.status_code}: {handler_response.text}"
            
            result_data = handler_response.json()
            assert "data" in result_data
            assert "message" in result_data
            
            # Wait for async processing
            time.sleep(3)
            
            # Verify order was created in database
            order_query = db_session.execute(
                text("SELECT id, numero_orden, estado, observaciones FROM ordenes WHERE id = :order_id"),
                {"order_id": order_id}
            ).fetchone()
            
            assert order_query is not None, "Order was not created in database"
            assert order_query[1] == order_data["numero_orden"]
            assert order_query[2] == "PENDIENTE", \
                f"Expected PENDIENTE, got {order_query[2]}. Observaciones: {order_query[3]}"
            
            # Verify stock was decreased in inventario database
            stock_query = db_session.execute(
                text("""
                    SELECT COALESCE(SUM(cantidad), 0) as total_stock
                    FROM inventario 
                    WHERE producto_id = :producto_id 
                    AND estado = 'DISPONIBLE'
                """),
                {"producto_id": sample_product_id}
            ).fetchone()
            
            remaining_stock = stock_query[0]
            expected_remaining = initial_stock - 80  # 150 - 80 = 70
            
            assert remaining_stock == expected_remaining, \
                f"Expected {expected_remaining} units remaining, got {remaining_stock}"
            
            # Verify FIFO/FEFO logic: LOTE-TEST-001 (expires sooner) should be consumed first
            lote1_query = db_session.execute(
                text("""
                    SELECT cantidad 
                    FROM inventario 
                    WHERE producto_id = :producto_id 
                    AND lote = 'LOTE-TEST-001'
                """),
                {"producto_id": sample_product_id}
            ).fetchone()
            
            lote2_query = db_session.execute(
                text("""
                    SELECT cantidad 
                    FROM inventario 
                    WHERE producto_id = :producto_id 
                    AND lote = 'LOTE-TEST-002'
                """),
                {"producto_id": sample_product_id}
            ).fetchone()
            
            # LOTE-TEST-001 should have: 100 - 80 = 20 units remaining
            # LOTE-TEST-002 should still have: 50 units (not touched yet)
            assert lote1_query[0] == 20, \
                f"LOTE-TEST-001 should have 20 units, got {lote1_query[0]}"
            assert lote2_query[0] == 50, \
                f"LOTE-TEST-002 should have 50 units, got {lote2_query[0]}"

    @pytest.mark.asyncio
    async def test_order_creation_with_insufficient_stock_fails(
        self,
        db_session,
        setup_inventory_stock,
        sample_product_id
    ):
        """
        Test that creating an order with insufficient stock:
        1. Fails stock decrease
        2. Marks order as CANCELADO
        3. Does not decrease any stock
        """
        initial_stock = setup_inventory_stock["total_stock"]  # 150
        
        # Prepare order data requesting more than available
        order_id = str(uuid.uuid4())
        order_data = {
            "id": order_id,
            "numero_orden": f"ORD-{uuid.uuid4().hex[:8].upper()}",
            "estado": "PENDIENTE",
            "id_cliente": str(uuid.uuid4()),
            "id_vendedor": str(uuid.uuid4()),
            "creado_por": str(uuid.uuid4()),
            "observaciones": "Integration test order - insufficient stock",
            "detalles": [
                {
                    "id_producto": sample_product_id,
                    "cantidad": 200,  # Request 200 units (only 150 available)
                    "precio_unitario": 100.0,
                    "observaciones": "Test product - insufficient"
                }
            ]
        }
        
        # Create Pub/Sub formatted message
        pubsub_message = create_pubsub_message(order_data)
        
        # Send order command to handler
        async with httpx.AsyncClient(timeout=30.0) as client:
            handler_response = await client.post(
                f"{ORDER_HANDLER_URL}/",
                json=pubsub_message,
                timeout=30.0
            )
            
            # Verify response (handler may still return 200 but order should be CANCELADO)
            assert handler_response.status_code == 200
            
            # Wait for async processing
            time.sleep(3)
            
            # Verify order was created but marked as CANCELADO
            order_query = db_session.execute(
                text("SELECT id, estado, observaciones FROM ordenes WHERE id = :order_id"),
                {"order_id": order_id}
            ).fetchone()
            
            assert order_query is not None, "Order was not created in database"
            assert order_query[1] == "CANCELADO", \
                f"Expected CANCELADO, got {order_query[1]}. Observaciones: {order_query[2]}"
            
            # Verify NO stock was decreased
            stock_query = db_session.execute(
                text("""
                    SELECT COALESCE(SUM(cantidad), 0) as total_stock
                    FROM inventario 
                    WHERE producto_id = :producto_id 
                    AND estado = 'DISPONIBLE'
                """),
                {"producto_id": sample_product_id}
            ).fetchone()
            
            remaining_stock = stock_query[0]
            assert remaining_stock == initial_stock, \
                f"Stock should remain at {initial_stock}, got {remaining_stock}"
            
            # Verify error message in observaciones
            observaciones = order_query[2]
            assert "ERROR_STOCK" in observaciones or "insuficiente" in observaciones.lower(), \
                f"Expected error message in observaciones, got: {observaciones}"

