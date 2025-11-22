# Quick Start - Pruebas E2E

Guía rápida para ejecutar las pruebas E2E en 5 minutos.

## Paso 1: Iniciar Servicios

```bash
docker-compose up -d
```

## Paso 2: Crear Datos de Prueba

### Opción A: Generar hashes y ejecutar SQL

```bash
# 1. Generar hashes de password
python tests/e2e/generate_password_hash.py

# 2. Seguir las instrucciones para actualizar el SQL

# 3. Ejecutar SQL actualizado
psql -h localhost -p 5480 -U postgres -d medisupply -f tests/e2e/seed_test_data_updated.sql
```

### Opción B: Crear usuarios manualmente

Si ya tienes usuarios de prueba, solo necesitas configurarlos:

```bash
# Copiar y configurar variables de entorno
cp tests/e2e/.env.e2e.example tests/e2e/.env.e2e

# Editar y ajustar los valores (emails, passwords, IDs)
nano tests/e2e/.env.e2e
```

## Paso 3: Limpiar Cache (IMPORTANTE)

Antes de ejecutar por primera vez o si re-ejecutas:

```bash
# Limpiar cache de Redis
docker compose exec redis redis-cli FLUSHALL

# Reiniciar servicio de inventario
docker compose restart inventario-service
```

## Paso 4: Ejecutar Pruebas

### Usando el script (recomendado)

```bash
./tests/e2e/run_e2e_tests.sh
```

### Usando pytest directamente

```bash
pytest tests/e2e/test_pedido_happy_path.py -v -s
```

## Paso 5: Verificación Rápida

Verifica que los servicios estén corriendo:

```bash
./tests/e2e/run_e2e_tests.sh --setup
```

## Troubleshooting Rápido

### Servicios no están corriendo
```bash
docker-compose ps
docker-compose up -d
```

### Error 401 (autenticación)
- Verifica que los usuarios existan en la BD
- Verifica que las credenciales en `.env.e2e` sean correctas

### Producto no existe
```bash
# Insertar producto de prueba rápidamente
psql -h localhost -p 5480 -U postgres -d medisupply << EOF
INSERT INTO productos (id, nombre, sku, precio_unitario)
VALUES ('11111111-1111-1111-1111-111111111111', 'Producto Test E2E', 'TEST_E2E_001', 15000.0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO inventario (producto_id, cantidad_disponible, estado)
VALUES ('11111111-1111-1111-1111-111111111111', 100, 'DISPONIBLE')
ON CONFLICT (producto_id) DO UPDATE SET cantidad_disponible = 100;
EOF
```

### Conductor o vehículo no existe
```bash
psql -h localhost -p 5480 -U postgres -d medisupply << EOF
INSERT INTO conductores (id, nombre, apellido, telefono, licencia)
VALUES (1, 'Juan', 'Pérez', '3001234567', 'ABC123')
ON CONFLICT (id) DO NOTHING;

INSERT INTO vehiculos (id, placa, marca, modelo, capacidad_kg)
VALUES (1, 'XYZ789', 'Chevrolet', 'NPR', 1500)
ON CONFLICT (id) DO NOTHING;
EOF
```

## Resultado Esperado

Si todo está bien, verás:

```
[PASO 1] Consultando inventario inicial...
  ✓ Inventario inicial: 100 unidades

[PASO 2] Creando pedido como cliente
  ✓ Pedido creado: abc123...

[PASO 3] Esperando descuento de inventario...
  ✓ Inventario actualizado correctamente

[PASO 4] Generando ruta de entrega
  ✓ Ruta creada: ID=1

[PASO 5] Verificando entrega programada
  ✓ CONFIRMACIÓN DE ENTREGA PROGRAMADA

✅ PRUEBA E2E COMPLETADA EXITOSAMENTE
```

## Más Información

Ver [README.md](README.md) para documentación completa.
