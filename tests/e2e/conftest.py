"""
Fixtures compartidos para pruebas E2E de MediSupply
"""
import pytest
import pytest_asyncio
import httpx
import os
from typing import Dict, Any


@pytest.fixture(scope="session")
def base_urls() -> Dict[str, str]:
    """
    URLs base de los servicios para las pruebas E2E.

    Pueden configurarse mediante variables de entorno.
    """
    return {
        "auth": os.getenv("AUTH_URL", "http://localhost:3012"),
        "mobile": os.getenv("BFF_MOBILE_URL", "http://localhost:3014"),
        "web": os.getenv("BFF_WEB_URL", "http://localhost:3013")
    }


@pytest_asyncio.fixture(scope="session")
async def auth_cliente(base_urls: Dict[str, str]) -> Dict[str, Any]:
    """
    Autentica un cliente de prueba y retorna el token JWT.

    Requiere que exista un usuario con role='client' en la base de datos.
    Configuración vía variables de entorno:
    - TEST_CLIENTE_EMAIL
    - TEST_CLIENTE_PASSWORD

    Returns:
        Dict con 'token' y 'headers' listos para usar en requests
    """
    email = os.getenv("TEST_CLIENTE_EMAIL", "cliente@test.com")
    password = os.getenv("TEST_CLIENTE_PASSWORD", "test123")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{base_urls['auth']}/auth/login",
            json={"email": email, "password": password}
        )

        if response.status_code != 200:
            raise Exception(
                f"Error al autenticar cliente: {response.status_code} - {response.text}"
            )

        data = response.json()
        return {
            "token": data["access_token"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "user_data": data
        }


@pytest_asyncio.fixture(scope="session")
async def auth_operador(base_urls: Dict[str, str]) -> Dict[str, Any]:
    """
    Autentica un operador/vendedor de prueba y retorna el token JWT.

    Requiere que exista un usuario con role='seller' en la base de datos.
    Configuración vía variables de entorno:
    - TEST_OPERADOR_EMAIL
    - TEST_OPERADOR_PASSWORD

    Returns:
        Dict con 'token' y 'headers' listos para usar en requests
    """
    email = os.getenv("TEST_OPERADOR_EMAIL", "operador@test.com")
    password = os.getenv("TEST_OPERADOR_PASSWORD", "test123")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{base_urls['auth']}/auth/login",
            json={"email": email, "password": password}
        )

        if response.status_code != 200:
            raise Exception(
                f"Error al autenticar operador: {response.status_code} - {response.text}"
            )

        data = response.json()
        return {
            "token": data["access_token"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "user_data": data
        }


@pytest.fixture(scope="session")
def datos_prueba() -> Dict[str, Any]:
    """
    IDs y datos de prueba necesarios para las pruebas E2E.

    Estos datos deben existir previamente en la base de datos.
    Configuración vía variables de entorno.

    Returns:
        Dict con IDs de producto, conductor, vehículo, etc.
    """
    return {
        "producto_id": os.getenv(
            "TEST_PRODUCTO_ID",
            "9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c"
        ),
        "producto_nombre": os.getenv("TEST_PRODUCTO_NOMBRE", "Producto Test E2E"),
        "conductor_id": int(os.getenv("TEST_CONDUCTOR_ID", "1")),
        "vehiculo_id": int(os.getenv("TEST_VEHICULO_ID", "1")),
        "bodega_origen": os.getenv("TEST_BODEGA", "Central Bogotá"),
        "direccion_entrega": os.getenv(
            "TEST_DIRECCION",
            "Calle 80 #45-20, Bogotá"
        ),
        "latitud": float(os.getenv("TEST_LATITUD", "4.7110")),
        "longitud": float(os.getenv("TEST_LONGITUD", "-74.0721")),
    }


@pytest.fixture(scope="session")
def timeouts() -> Dict[str, int]:
    """
    Timeouts para operaciones que pueden tardar debido a eventual consistency.

    Returns:
        Dict con timeouts en segundos para diferentes operaciones
    """
    return {
        "inventario_update": int(os.getenv("TIMEOUT_INVENTARIO", "10")),
        "order_status": int(os.getenv("TIMEOUT_ORDER_STATUS", "10")),
        "polling_interval": float(os.getenv("POLLING_INTERVAL", "1.0"))
    }
