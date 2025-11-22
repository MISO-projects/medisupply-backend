"""
Prueba E2E del Happy Path: Pedido → Inventario → Ruta → Confirmación de Entrega

Esta prueba valida el flujo completo del sistema desde que un cliente crea un pedido
hasta que se confirma una entrega programada con fecha estimada.

Flujo:
1. Cliente crea pedido
2. Sistema descuenta inventario automáticamente
3. Operador genera ruta de entrega
4. Se confirma que existe entrega programada para el pedido
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime


class TestHappyPathPedidoCompleto:
    """
    Suite de pruebas E2E para el happy path de pedidos en MediSupply.
    """

    @pytest.mark.asyncio
    async def test_flujo_completo_pedido_a_entrega_programada(
        self,
        base_urls: Dict[str, str],
        auth_cliente: Dict[str, Any],
        auth_operador: Dict[str, Any],
        datos_prueba: Dict[str, Any],
        timeouts: Dict[str, int]
    ):
        """
        Prueba E2E del happy path completo:
        Pedido → Inventario → Ruta → Confirmación de Entrega

        Valida:
        - Creación exitosa de pedido
        - Descuento automático de inventario
        - Generación de ruta con el pedido
        - Confirmación de entrega programada
        """
        producto_id = datos_prueba["producto_id"]
        cantidad_pedido = 2
        precio_unitario = 15000.0

        # ========================================================================
        # PASO 1: Obtener inventario inicial del producto
        # ========================================================================
        print(f"\n[PASO 1] Consultando inventario inicial del producto {producto_id}")

        inventario_inicial = await self._obtener_inventario_producto(
            base_urls["mobile"],
            auth_cliente["headers"],
            producto_id
        )

        print(f"  ✓ Inventario inicial: {inventario_inicial} unidades")

        # Verificar que hay suficiente inventario
        assert inventario_inicial >= cantidad_pedido, (
            f"Inventario insuficiente. Disponible: {inventario_inicial}, "
            f"Requerido: {cantidad_pedido}"
        )

        # ========================================================================
        # PASO 2: Cliente crea pedido
        # ========================================================================
        print(f"\n[PASO 2] Creando pedido como cliente")

        pedido = await self._crear_pedido_cliente(
            base_urls["mobile"],
            auth_cliente["headers"],
            producto_id,
            cantidad_pedido,
            precio_unitario
        )

        pedido_id = pedido["id"]
        print(f"  ✓ Pedido creado: {pedido_id}")

        # Imprimir info disponible (opcional)
        if "estado" in pedido:
            print(f"  ✓ Estado: {pedido['estado']}")
        if "fecha_entrega_estimada" in pedido:
            print(f"  ✓ Fecha entrega estimada: {pedido['fecha_entrega_estimada']}")

        # ========================================================================
        # PASO 3: Esperar y verificar descuento de inventario (eventual consistency)
        # ========================================================================
        print(f"\n[PASO 3] Esperando descuento de inventario...")

        inventario_esperado = inventario_inicial - cantidad_pedido

        inventario_actual = await self._esperar_actualizacion_inventario(
            base_urls["mobile"],
            auth_cliente["headers"],
            producto_id,
            inventario_esperado,
            timeout=timeouts["inventario_update"],
            polling_interval=timeouts["polling_interval"]
        )

        print(f"  ✓ Inventario actualizado correctamente")
        print(f"    Antes: {inventario_inicial} → Después: {inventario_actual}")
        print(f"    Descontado: {inventario_inicial - inventario_actual} unidades")

        assert inventario_actual == inventario_esperado, (
            f"Inventario no se descontó correctamente. "
            f"Esperado: {inventario_esperado}, Actual: {inventario_actual}"
        )

        # ========================================================================
        # PASO 4: Operador genera ruta de entrega
        # ========================================================================
        print(f"\n[PASO 4] Generando ruta de entrega como operador")

        ruta = await self._crear_ruta(
            base_urls["web"],
            auth_operador["headers"],
            pedido_id,
            datos_prueba
        )

        ruta_id = ruta["id"]
        print(f"  ✓ Ruta creada: ID={ruta_id}")
        print(f"  ✓ {ruta.get('mensaje', 'Ruta creada exitosamente')}")

        # ========================================================================
        # PASO 5: Verificar confirmación de entrega programada
        # ========================================================================
        print(f"\n[PASO 5] Verificando entrega programada")

        entrega_programada = await self._obtener_ruta_con_detalles(
            base_urls["web"],
            auth_operador["headers"],
            ruta_id
        )

        print(f"  ✓ Ruta obtenida: ID={entrega_programada['id']}")
        print(f"  ✓ Estado de ruta: {entrega_programada['estado']}")
        print(f"  ✓ Fecha de entrega: {entrega_programada['fecha']}")
        print(f"  ✓ Número de paradas: {len(entrega_programada['paradas'])}")

        # Validar que la ruta tiene el pedido
        assert len(entrega_programada["paradas"]) > 0, (
            "La ruta no tiene paradas"
        )

        parada_pedido = next(
            (p for p in entrega_programada["paradas"] if p["pedido_id"] == pedido_id),
            None
        )

        assert parada_pedido is not None, (
            f"El pedido {pedido_id} no está en la ruta"
        )

        print(f"\n  ✓ CONFIRMACIÓN DE ENTREGA PROGRAMADA:")
        print(f"    - Pedido ID: {parada_pedido['pedido_id']}")
        print(f"    - Dirección: {parada_pedido['direccion']}")
        print(f"    - Contacto: {parada_pedido['contacto']}")
        print(f"    - Estado parada: {parada_pedido['estado']}")
        print(f"    - Orden en ruta: {parada_pedido['orden']}")

        if parada_pedido.get("pedido"):
            pedido_info = parada_pedido["pedido"]
            print(f"    - Número de orden: {pedido_info.get('numero_orden', 'N/A')}")
            print(f"    - Cliente: {pedido_info.get('nombre_cliente', 'N/A')}")
            print(f"    - Valor total: ${pedido_info.get('valor_total', 0):,.2f}")

        # Validaciones finales
        assert parada_pedido["estado"] == "Pendiente", (
            f"Estado de parada inesperado: {parada_pedido['estado']}"
        )
        assert entrega_programada["vehiculo_id"] == datos_prueba["vehiculo_id"], (
            "Vehículo asignado no coincide"
        )
        assert entrega_programada["conductor_id"] == datos_prueba["conductor_id"], (
            "Conductor asignado no coincide"
        )

        print(f"\n✅ PRUEBA E2E COMPLETADA EXITOSAMENTE")
        print(f"   Happy path validado: Pedido → Inventario → Ruta → Confirmación")

    # ========================================================================
    # Métodos auxiliares
    # ========================================================================

    async def _obtener_inventario_producto(
        self,
        base_url: str,
        headers: Dict[str, str],
        producto_id: str
    ) -> int:
        """
        Obtiene la cantidad disponible de un producto en inventario.

        Args:
            base_url: URL base del BFF-Mobile
            headers: Headers con token de autenticación
            producto_id: UUID del producto

        Returns:
            Cantidad disponible en inventario
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/movil/inventario/",
                headers=headers,
                params={
                    "page": 1,
                    "page_size": 100
                }
            )

            if response.status_code != 200:
                raise Exception(
                    f"Error al obtener inventario: {response.status_code} - {response.text}"
                )

            data = response.json()

            # Buscar el producto en los resultados
            for item in data.get("items", []):
                if item.get("producto_id") == producto_id:
                    return item.get("cantidad", 0)

            raise Exception(f"Producto {producto_id} no encontrado en inventario")

    async def _crear_pedido_cliente(
        self,
        base_url: str,
        headers: Dict[str, str],
        producto_id: str,
        cantidad: int,
        precio_unitario: float
    ) -> Dict[str, Any]:
        """
        Crea un pedido como cliente.

        Args:
            base_url: URL base del BFF-Mobile
            headers: Headers con token de autenticación del cliente
            producto_id: UUID del producto
            cantidad: Cantidad a pedir
            precio_unitario: Precio unitario del producto

        Returns:
            Datos del pedido creado
        """
        payload = {
            "observaciones": "Pedido E2E Test - Happy Path",
            "detalles": [
                {
                    "id_producto": producto_id,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "observaciones": "Producto de prueba E2E"
                }
            ]
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/movil/ordenes/cliente",
                headers=headers,
                json=payload
            )

            if response.status_code not in [200, 201]:
                raise Exception(
                    f"Error al crear pedido: {response.status_code} - {response.text}"
                )

            return response.json()

    async def _esperar_actualizacion_inventario(
        self,
        base_url: str,
        headers: Dict[str, str],
        producto_id: str,
        inventario_esperado: int,
        timeout: int = 10,
        polling_interval: float = 1.0
    ) -> int:
        """
        Espera a que el inventario se actualice (eventual consistency).

        Realiza polling hasta que el inventario tenga el valor esperado
        o se alcance el timeout.

        Args:
            base_url: URL base del BFF-Mobile
            headers: Headers con token de autenticación
            producto_id: UUID del producto
            inventario_esperado: Cantidad esperada en inventario
            timeout: Tiempo máximo de espera en segundos
            polling_interval: Intervalo entre consultas en segundos

        Returns:
            Cantidad actual en inventario

        Raises:
            TimeoutError: Si el inventario no se actualiza en el tiempo esperado
        """
        intentos = int(timeout / polling_interval)

        for intento in range(1, intentos + 1):
            inventario_actual = await self._obtener_inventario_producto(
                base_url, headers, producto_id
            )

            if inventario_actual == inventario_esperado:
                print(f"  ✓ Inventario actualizado en intento {intento}/{intentos}")
                return inventario_actual

            print(f"  ⏳ Intento {intento}/{intentos}: Inventario={inventario_actual}, "
                  f"Esperado={inventario_esperado}")

            if intento < intentos:
                await asyncio.sleep(polling_interval)

        raise TimeoutError(
            f"Inventario no se actualizó después de {timeout}s. "
            f"Último valor: {inventario_actual}, Esperado: {inventario_esperado}"
        )

    async def _crear_ruta(
        self,
        base_url: str,
        headers: Dict[str, str],
        pedido_id: str,
        datos_prueba: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea una ruta de entrega como operador.

        Args:
            base_url: URL base del BFF-Web
            headers: Headers con token de autenticación del operador
            pedido_id: UUID del pedido a incluir en la ruta
            datos_prueba: Datos de prueba (conductor, vehículo, etc.)

        Returns:
            Datos de la ruta creada
        """
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "fecha": fecha_hoy,
            "bodega_origen": datos_prueba["bodega_origen"],
            "estado": "Pendiente",
            "vehiculo_id": datos_prueba["vehiculo_id"],
            "conductor_id": datos_prueba["conductor_id"],
            "condiciones_almacenamiento": "Refrigerado",
            "paradas": [
                {
                    "pedido_id": pedido_id,
                    "direccion": datos_prueba["direccion_entrega"],
                    "contacto": "Cliente Test E2E",
                    "latitud": datos_prueba["latitud"],
                    "longitud": datos_prueba["longitud"]
                }
            ]
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/web/logistica/rutas",
                headers=headers,
                json=payload
            )

            if response.status_code not in [200, 201]:
                raise Exception(
                    f"Error al crear ruta: {response.status_code} - {response.text}"
                )

            return response.json()

    async def _obtener_ruta_con_detalles(
        self,
        base_url: str,
        headers: Dict[str, str],
        ruta_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene los detalles completos de una ruta.

        Args:
            base_url: URL base del BFF-Web
            headers: Headers con token de autenticación del operador
            ruta_id: ID de la ruta

        Returns:
            Datos completos de la ruta con paradas y pedidos
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/web/logistica/rutas/{ruta_id}",
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(
                    f"Error al obtener ruta: {response.status_code} - {response.text}"
                )

            return response.json()
