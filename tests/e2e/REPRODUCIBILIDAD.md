# 🔄 Guía de Reproducibilidad - Pruebas E2E

Este documento garantiza que las pruebas E2E puedan ejecutarse de manera consistente en cualquier máquina.

## ✅ Archivos Actualizados con Correcciones

Todos los archivos ya están actualizados con las correcciones realizadas durante la implementación:

### 1. **seed_test_data.sql** ✅
- ✅ UUIDs v4 válidos (reemplazan los genéricos 11111111-..., 22222222-..., etc.)
- ✅ `fecha_actualizacion` incluida para `clientes_institucionales`
- ✅ Todos los campos requeridos completos
- ✅ Orden correcto de inserción (respetando foreign keys)

**IDs importantes:**
```sql
PRODUCTO_ID:  9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c
INVENTARIO_ID: e482bf52-8136-428c-b4b4-f7eb21b5d74e
CLIENTE_ID:    3488e55b-02cb-43c4-aeb2-dcc51617790e
VENDEDOR_ID:   0cfe7958-719d-4dcb-b408-690f750592bd
```

### 2. **conftest.py** ✅
- ✅ UUID del producto actualizado a v4 válido
- ✅ Fixtures async con `@pytest_asyncio.fixture`
- ✅ Token JWT usando `access_token` (no `token`)

### 3. **test_pedido_happy_path.py** ✅
- ✅ Estructura JSON correcta: `data.get("items")` en lugar de `data.get("inventario")`
- ✅ Campo de cantidad: `item.get("cantidad")` en lugar de `cantidad_disponible`
- ✅ Validaciones opcionales para campos que pueden no existir

### 4. **.env.e2e.example** ✅
- ✅ UUID del producto actualizado
- ✅ Comentarios indicando que coincide con `seed_test_data.sql`

## 🚀 Setup Automatizado (Opción Recomendada)

Para configurar todo automáticamente:

```bash
# Ejecutar script de setup
./tests/e2e/setup_e2e.sh
```

Este script hace:
1. ✅ Verifica que los servicios estén corriendo
2. ✅ Limpia cache de Redis
3. ✅ Reinicia servicio de inventario
4. ✅ Inserta datos de prueba
5. ✅ Verifica que todo esté OK

## 🔧 Setup Manual (Paso a Paso)

Si prefieres hacerlo manualmente:

### 1. Iniciar Servicios

```bash
docker compose --profile dev up -d
```

### 2. Limpiar Cache de Redis ⚠️ CRÍTICO

```bash
# Limpiar cache
docker compose exec redis redis-cli FLUSHALL

# Reiniciar servicio de inventario
docker compose restart inventario-service
```

**POR QUÉ ES IMPORTANTE:**
El servicio de inventario cachea datos en Redis. Si hay UUIDs antiguos o inválidos en cache, las pruebas fallarán con errores de validación de UUIDs v4.

### 3. Insertar Datos de Prueba

```bash
PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
  -f tests/e2e/seed_test_data.sql
```

### 4. Ejecutar Pruebas

```bash
pytest tests/e2e/test_pedido_happy_path.py -v -s
```

## 🔁 Re-ejecución de Pruebas

Si necesitas ejecutar las pruebas múltiples veces:

```bash
# Opción 1: Re-ejecutar setup completo
./tests/e2e/setup_e2e.sh

# Opción 2: Solo limpiar cache y re-ejecutar
docker compose exec redis redis-cli FLUSHALL
docker compose restart inventario-service
pytest tests/e2e/test_pedido_happy_path.py -v -s
```

## 📋 Checklist de Verificación

Antes de ejecutar pruebas, verifica:

- [ ] Servicios corriendo: `docker compose ps`
- [ ] Cache de Redis limpio (si re-ejecutas)
- [ ] Datos de prueba en BD:
  ```bash
  PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
    -c "SELECT COUNT(*) FROM users WHERE email IN ('cliente@test.com', 'operador@test.com');"
  # Debe retornar: 2
  ```

## 🐛 Problemas Comunes y Soluciones

### Error: UUID version 4 expected

**Causa:** Cache de Redis tiene UUIDs antiguos

**Solución:**
```bash
docker compose exec redis redis-cli FLUSHALL
docker compose restart inventario-service
```

### Error: 500 Internal Server Error en inventario

**Causa:** Cache de Redis desactualizado

**Solución:** Misma que arriba (limpiar cache)

### Error: Error interno al obtener información del cliente

**Causa:** Campo `fecha_actualizacion` NULL en tabla `clientes_institucionales`

**Solución:**
```bash
# Ya está corregido en seed_test_data.sql
# Si persiste, ejecutar:
PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
  -c "UPDATE clientes_institucionales SET fecha_actualizacion = NOW() WHERE fecha_actualizacion IS NULL;"
```

### Error: Producto no encontrado en inventario

**Causa:** Campo JSON incorrecto o producto no en BD

**Solución:**
1. Verificar que se ejecutó `seed_test_data.sql`
2. El test usa `data.get("items")` (ya corregido)

## 📊 Validación Post-Setup

Para verificar que todo está listo:

```bash
# Ejecutar verificación de setup
./tests/e2e/run_e2e_tests.sh --setup
```

O manualmente:

```bash
# 1. Verificar usuarios
PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
  -c "SELECT email, role FROM users WHERE email IN ('cliente@test.com', 'operador@test.com');"

# 2. Verificar producto
PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
  -c "SELECT id, nombre, sku FROM productos WHERE sku = 'TEST_E2E_001';"

# 3. Verificar inventario
PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
  -c "SELECT producto_id, cantidad FROM inventario WHERE producto_id = '9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c';"
```

## 🌍 En Otra Máquina

Para ejecutar en la máquina de un colega:

```bash
# 1. Clonar/pull del repo
git pull

# 2. Iniciar servicios
docker compose --profile dev up -d

# 3. Ejecutar setup automático
./tests/e2e/setup_e2e.sh

# 4. Ejecutar pruebas
pytest tests/e2e/test_pedido_happy_path.py -v -s
```

**¡Eso es todo!** Todo está listo para ser 100% reproducible.

## 📝 Resumen de Garantías

✅ **Todos los archivos están actualizados** con las correcciones necesarias
✅ **Script de setup automatizado** (`setup_e2e.sh`) hace todo el trabajo
✅ **Documentación completa** en README.md y QUICKSTART.md
✅ **UUIDs v4 válidos** en todos los datos de prueba
✅ **Instrucciones de limpieza de cache** documentadas
✅ **Troubleshooting completo** para problemas comunes

**No se necesita ninguna modificación manual adicional. Todo está listo para ejecutarse.**
