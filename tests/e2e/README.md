# Pruebas E2E - MediSupply Backend

Este directorio contiene las pruebas End-to-End (E2E) para validar el flujo completo del sistema MediSupply.

## Happy Path Implementado

**Pedido → Inventario → Ruta → Confirmación de Entrega**

La prueba valida:
1. ✅ Cliente crea un pedido
2. ✅ Sistema descuenta inventario automáticamente
3. ✅ Operador genera ruta de entrega
4. ✅ Se confirma que existe entrega programada para el pedido

---

## Prerequisitos

### 1. Servicios en Ejecución

Todos los servicios necesarios deben estar corriendo:

```bash
# Iniciar todos los servicios
docker-compose up -d

# Verificar que están corriendo
docker-compose ps
```

**Servicios requeridos:**
- `autenticacion` (puerto 3012)
- `bff-movil` (puerto 3014)
- `bff-web` (puerto 3013)
- `inventario` (puerto 3008)
- `ordenes-command-api` (puerto 3000)
- `ordenes-command-handler` (puerto 3001)
- `ordenes-query-api` (puerto 3002)
- `logistica` (puerto 3007)
- `postgres` (puerto 5480)
- `redis` (puerto 6379)
- `pubsub-emulator` (puerto 8085)

### 2. Datos de Prueba en Base de Datos

Las pruebas requieren datos específicos en la base de datos. Puedes crearlos manualmente o usar un script de seed.

#### Usuarios de Prueba

```sql
-- Cliente de prueba (role='client')
INSERT INTO usuarios (id, email, password_hash, role, id_client)
VALUES (
    gen_random_uuid(),
    'cliente@test.com',
    -- Password: test123 (hash con Argon2)
    '$argon2id$v=19$m=65536,t=3,p=4$...',
    'client',
    'cliente-uuid-aqui'
);

-- Operador de prueba (role='seller')
INSERT INTO usuarios (id, email, password_hash, role, id_seller)
VALUES (
    gen_random_uuid(),
    'operador@test.com',
    -- Password: test123 (hash con Argon2)
    '$argon2id$v=19$m=65536,t=3,p=4$...',
    'seller',
    'vendedor-uuid-aqui'
);
```

**Nota:** Para generar el hash de password, puedes usar el endpoint de registro o generar el hash manualmente con Argon2.

#### Conductor

```sql
INSERT INTO conductores (id, nombre, apellido, telefono, licencia)
VALUES (
    1,
    'Juan',
    'Pérez',
    '3001234567',
    'ABC123'
)
ON CONFLICT (id) DO NOTHING;
```

#### Vehículo

```sql
INSERT INTO vehiculos (id, placa, marca, modelo, capacidad_kg)
VALUES (
    1,
    'XYZ789',
    'Chevrolet',
    'NPR',
    1500
)
ON CONFLICT (id) DO NOTHING;
```

#### Producto e Inventario

```sql
-- Producto de prueba
INSERT INTO productos (id, nombre, sku, precio_unitario, categoria, descripcion)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Producto Test E2E',
    'TEST_E2E_001',
    15000.0,
    'Medicamentos',
    'Producto de prueba para tests E2E'
)
ON CONFLICT (id) DO NOTHING;

-- Inventario suficiente
INSERT INTO inventario (producto_id, cantidad_disponible, estado, ubicacion)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    100,
    'DISPONIBLE',
    'Bodega Central'
)
ON CONFLICT (producto_id) DO UPDATE SET cantidad_disponible = 100;
```

### 3. Dependencias de Python

Las dependencias ya deberían estar instaladas si tienes el proyecto configurado:

```bash
pip install pytest pytest-asyncio httpx python-dotenv
```

---

## Configuración

### Variables de Entorno

Puedes configurar las pruebas mediante variables de entorno. Crea un archivo `.env.e2e` en este directorio:

```bash
# URLs de servicios
AUTH_URL=http://localhost:3012
BFF_MOBILE_URL=http://localhost:3014
BFF_WEB_URL=http://localhost:3013

# Credenciales de usuarios de prueba
TEST_CLIENTE_EMAIL=cliente@test.com
TEST_CLIENTE_PASSWORD=test123
TEST_OPERADOR_EMAIL=operador@test.com
TEST_OPERADOR_PASSWORD=test123

# IDs de datos de prueba
TEST_PRODUCTO_ID=11111111-1111-1111-1111-111111111111
TEST_PRODUCTO_NOMBRE=Producto Test E2E
TEST_CONDUCTOR_ID=1
TEST_VEHICULO_ID=1
TEST_BODEGA=Central Bogotá
TEST_DIRECCION=Calle 80 #45-20, Bogotá
TEST_LATITUD=4.7110
TEST_LONGITUD=-74.0721

# Timeouts (segundos)
TIMEOUT_INVENTARIO=10
TIMEOUT_ORDER_STATUS=10
POLLING_INTERVAL=1.0
```

---

## Preparación Antes de Ejecutar

### Limpiar Cache de Redis (IMPORTANTE si re-ejecutas)

Si ejecutas las pruebas múltiples veces o si actualizaste los datos de prueba, **debes limpiar el cache de Redis** para evitar errores de validación con UUIDs antiguos:

```bash
# Limpiar cache de Redis
docker compose exec redis redis-cli FLUSHALL

# Reiniciar servicio de inventario (recomendado)
docker compose restart inventario-service
```

**Cuándo limpiar el cache:**
- Primera vez ejecutando las pruebas
- Después de actualizar `seed_test_data.sql`
- Si ves errores de validación de UUIDs
- Si modificas datos de prueba en la BD

---

## Ejecución

### Ejecutar la Prueba E2E

Desde la raíz del proyecto:

```bash
# Ejecutar la prueba con output detallado
pytest tests/e2e/test_pedido_happy_path.py -v -s

# Con timeout global de 60 segundos
pytest tests/e2e/test_pedido_happy_path.py -v -s --timeout=60

# Ver más detalles en caso de error
pytest tests/e2e/test_pedido_happy_path.py -v -s --tb=long
```

### Ejecutar Todas las Pruebas E2E

```bash
pytest tests/e2e/ -v -s
```

### Modo Específico (solo si falla algún paso)

```bash
# Solo la prueba específica por nombre
pytest tests/e2e/test_pedido_happy_path.py::TestHappyPathPedidoCompleto::test_flujo_completo_pedido_a_entrega_programada -v -s
```

---

## Salida Esperada

Si todo está configurado correctamente, deberías ver una salida similar a:

```
tests/e2e/test_pedido_happy_path.py::TestHappyPathPedidoCompleto::test_flujo_completo_pedido_a_entrega_programada

[PASO 1] Consultando inventario inicial del producto 11111111-1111-1111-1111-111111111111
  ✓ Inventario inicial: 100 unidades

[PASO 2] Creando pedido como cliente
  ✓ Pedido creado: abc123-def456-...
  ✓ Estado: PENDIENTE
  ✓ Fecha entrega estimada: 2025-08-19T10:30:00

[PASO 3] Esperando descuento de inventario...
  ⏳ Intento 1/10: Inventario=100, Esperado=98
  ⏳ Intento 2/10: Inventario=100, Esperado=98
  ✓ Inventario actualizado en intento 3/10
  ✓ Inventario actualizado correctamente
    Antes: 100 → Después: 98
    Descontado: 2 unidades

[PASO 4] Generando ruta de entrega como operador
  ✓ Ruta creada: ID=1
  ✓ Ruta creada exitosamente

[PASO 5] Verificando entrega programada
  ✓ Ruta obtenida: ID=1
  ✓ Estado de ruta: Pendiente
  ✓ Fecha de entrega: 2025-08-17
  ✓ Número de paradas: 1

  ✓ CONFIRMACIÓN DE ENTREGA PROGRAMADA:
    - Pedido ID: abc123-def456-...
    - Dirección: Calle 80 #45-20, Bogotá
    - Contacto: Cliente Test E2E
    - Estado parada: Pendiente
    - Orden en ruta: 1
    - Número de orden: ORD-2025-001
    - Cliente: Cliente Test
    - Valor total: $30,000.00

✅ PRUEBA E2E COMPLETADA EXITOSAMENTE
   Happy path validado: Pedido → Inventario → Ruta → Confirmación

PASSED
```

---

## Troubleshooting

### Error: Connection refused

**Problema:** No se puede conectar a un servicio.

**Solución:**
```bash
# Verificar que todos los servicios estén corriendo
docker-compose ps

# Iniciar servicios faltantes
docker-compose up -d
```

### Error: 401 Unauthorized

**Problema:** Autenticación fallida.

**Solución:**
- Verificar que los usuarios de prueba existan en la base de datos
- Verificar que las credenciales en `.env.e2e` sean correctas
- Verificar que el servicio de autenticación esté corriendo

### Error: Producto no encontrado en inventario

**Problema:** El producto de prueba no existe.

**Solución:**
```sql
-- Insertar producto e inventario de prueba
INSERT INTO productos (id, nombre, sku, precio_unitario)
VALUES ('11111111-1111-1111-1111-111111111111', 'Producto Test E2E', 'TEST_E2E_001', 15000.0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO inventario (producto_id, cantidad_disponible, estado)
VALUES ('11111111-1111-1111-1111-111111111111', 100, 'DISPONIBLE')
ON CONFLICT (producto_id) DO UPDATE SET cantidad_disponible = 100;
```

### Error: conductor_id no existe

**Problema:** No existe el conductor en la base de datos.

**Solución:**
```sql
INSERT INTO conductores (id, nombre, apellido, telefono, licencia)
VALUES (1, 'Juan', 'Pérez', '3001234567', 'ABC123')
ON CONFLICT (id) DO NOTHING;
```

### Error: TimeoutError - Inventario no se actualizó

**Problema:** El inventario no se descontó en el tiempo esperado (eventual consistency).

**Solución:**
1. Verificar que el `ordenes-command-handler` esté corriendo
2. Verificar que el `inventario` service esté corriendo
3. Verificar logs del handler: `docker-compose logs ordenes-command-handler`
4. Aumentar el timeout en `.env.e2e`: `TIMEOUT_INVENTARIO=20`

### Error: Inventario insuficiente

**Problema:** No hay suficiente inventario para el producto.

**Solución:**
```sql
UPDATE inventario
SET cantidad_disponible = 100
WHERE producto_id = '11111111-1111-1111-1111-111111111111';
```

---

## Integración con CI/CD

### GitHub Actions

Ejemplo de workflow:

```yaml
name: E2E Tests

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Seed test data
        run: python scripts/seed_e2e_data.py

      - name: Run E2E tests
        run: pytest tests/e2e/ -v --timeout=60

      - name: Stop services
        if: always()
        run: docker-compose down
```

---

## Mantenimiento

### Limpiar Datos de Prueba

Si necesitas resetear los datos de prueba:

```bash
# Opción 1: Reset completo de base de datos
docker-compose down -v
docker-compose up -d

# Opción 2: Limpiar solo datos específicos
psql -h localhost -p 5480 -U postgres -d medisupply << EOF
DELETE FROM paradas WHERE pedido_id IN (
  SELECT id FROM ordenes WHERE observaciones LIKE '%E2E Test%'
);
DELETE FROM rutas WHERE id IN (
  SELECT DISTINCT ruta_id FROM paradas WHERE pedido_id IN (
    SELECT id FROM ordenes WHERE observaciones LIKE '%E2E Test%'
  )
);
DELETE FROM detalles_orden WHERE orden_id IN (
  SELECT id FROM ordenes WHERE observaciones LIKE '%E2E Test%'
);
DELETE FROM ordenes WHERE observaciones LIKE '%E2E Test%';
EOF
```

---

## Estructura de Archivos

```
tests/e2e/
├── __init__.py                     # Inicialización del módulo
├── conftest.py                     # Fixtures compartidos (auth, datos)
├── test_pedido_happy_path.py       # Prueba principal del happy path
├── README.md                       # Esta documentación
└── .env.e2e                        # Variables de entorno (opcional)
```

---

## Próximos Pasos

Para mejorar la cobertura de pruebas E2E, considera:

1. **Más escenarios**: Pedidos con múltiples productos, rutas con múltiples paradas
2. **Casos de error**: Inventario insuficiente, producto no encontrado, etc.
3. **Limpieza automática**: Fixtures con cleanup después de cada prueba
4. **Paralelización**: Ejecutar múltiples pruebas en paralelo
5. **Métricas**: Tiempo de ejecución, tasa de éxito histórica

---

## Soporte

Para problemas o preguntas sobre las pruebas E2E:
1. Revisa la sección de Troubleshooting
2. Verifica los logs de los servicios: `docker-compose logs [servicio]`
3. Consulta la documentación de la API en `/docs` de cada BFF
