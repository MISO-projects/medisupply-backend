-- ============================================================================
-- Script de Seed para Datos de Prueba E2E - MediSupply
-- ============================================================================
-- Este script crea los datos necesarios para ejecutar las pruebas E2E
-- Ajustado para los esquemas reales de la base de datos
--
-- Ejecución:
-- PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db -f tests/e2e/seed_test_data.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PLAN DE VENTA (necesario para vendedores)
-- ============================================================================
INSERT INTO planes_venta (id, nombre, descripcion, fecha_inicio, fecha_fin, meta_venta, fecha_creacion)
VALUES (
    'b9a4f875-7443-4d88-a3b7-76fd8ff6c3f9',
    'Plan Test E2E',
    'Plan de venta para pruebas E2E',
    '2024-01-01',
    '2026-12-31',
    1000000.00,
    NOW()
)
ON CONFLICT (nombre) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    fecha_fin = EXCLUDED.fecha_fin;

-- ============================================================================
-- 2. VENDEDOR DE PRUEBA
-- ============================================================================
INSERT INTO vendedores (id, nombre, documento_identidad, email, zona_asignada, plan_venta_id, fecha_creacion)
VALUES (
    '0cfe7958-719d-4dcb-b408-690f750592bd',
    'Operador Test',
    '1234567890',
    'operador@test.com',
    'Bogotá Centro',
    'b9a4f875-7443-4d88-a3b7-76fd8ff6c3f9',
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    zona_asignada = EXCLUDED.zona_asignada;

-- ============================================================================
-- 3. CLIENTE INSTITUCIONAL DE PRUEBA
-- ============================================================================
INSERT INTO clientes_institucionales (id, nombre, nit, address, id_vendedor, fecha_creacion, fecha_actualizacion)
VALUES (
    '3488e55b-02cb-43c4-aeb2-dcc51617790e',
    'Cliente Test E2E',
    '900123456-7',
    'Calle 80 #45-20, Bogotá',
    '0cfe7958-719d-4dcb-b408-690f750592bd',
    NOW(),
    NOW()
)
ON CONFLICT (nit) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    address = EXCLUDED.address,
    fecha_actualizacion = NOW();

-- ============================================================================
-- 4. USUARIOS DE PRUEBA
-- ============================================================================
-- Usuario Cliente (Password: test123)
INSERT INTO users (id, email, username, role, hashed_password, is_active, id_client, created_at)
VALUES (
    '27e549b2-6b63-47b3-9939-9b4720a8fd94',
    'cliente@test.com',
    'cliente_test',
    'client',
    '$argon2id$v=19$m=65536,t=3,p=4$Za3Q8Bl1et3Rj4NHwIZGAQ$zqJP8nhjNnhAQLGBZtgbafzB+wl8T+BCrh0TcyA73JA',
    true,
    '3488e55b-02cb-43c4-aeb2-dcc51617790e',
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    role = EXCLUDED.role,
    id_client = EXCLUDED.id_client,
    hashed_password = EXCLUDED.hashed_password,
    is_active = true;

-- Usuario Operador/Vendedor (Password: test123)
INSERT INTO users (id, email, username, role, hashed_password, is_active, id_seller, created_at)
VALUES (
    'e553f968-8da4-4720-a3e0-1cb80812b065',
    'operador@test.com',
    'operador_test',
    'seller',
    '$argon2id$v=19$m=65536,t=3,p=4$orGeV/lAUAoIRV3fULVwvA$tln+2ZfIaKWLbRiWAn59ZH3YZvHc/pbIl2bKqPOEAPU',
    true,
    '0cfe7958-719d-4dcb-b408-690f750592bd',
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    role = EXCLUDED.role,
    id_seller = EXCLUDED.id_seller,
    hashed_password = EXCLUDED.hashed_password,
    is_active = true;

-- ============================================================================
-- 5. CONDUCTOR DE PRUEBA
-- ============================================================================
INSERT INTO conductores (id, nombre, apellido, documento, telefono, email, licencia_conducir, activo, fecha_creacion)
VALUES (
    1,
    'Juan',
    'Pérez',
    '1234567890',
    '3001234567',
    'conductor.test@medisupply.com',
    'ABC123',
    true,
    NOW()
)
ON CONFLICT (documento) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    activo = true;

-- ============================================================================
-- 6. VEHÍCULO DE PRUEBA
-- ============================================================================
INSERT INTO vehiculos (id, placa, marca, modelo, tipo, capacidad_kg, activo, fecha_creacion)
VALUES (
    1,
    'XYZ789',
    'Chevrolet',
    'NPR',
    'Camión',
    1500,
    true,
    NOW()
)
ON CONFLICT (placa) DO UPDATE SET
    marca = EXCLUDED.marca,
    modelo = EXCLUDED.modelo,
    activo = true;

-- ============================================================================
-- 7. PROVEEDOR DE PRUEBA (necesario para productos)
-- ============================================================================
INSERT INTO proveedores (id, nombre, id_tributario, tipo_proveedor, email, pais, contacto, fecha_creacion)
VALUES (
    '7ec13a5e-c1de-4f9a-a1eb-7c2b6d24ee76',
    'Proveedor Test E2E',
    '800111222-3',
    'Nacional',
    'proveedor.test@medisupply.com',
    'Colombia',
    'Juan Pérez - 3009876543',
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre;

-- ============================================================================
-- 8. PRODUCTO DE PRUEBA
-- ============================================================================
INSERT INTO productos (
    id,
    nombre,
    sku,
    precio_unitario,
    categoria,
    descripcion,
    disponible,
    unidad_medida,
    tipo_almacenamiento,
    proveedor_id,
    proveedor_nombre,
    created_at
)
VALUES (
    '9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c',
    'Producto Test E2E',
    'TEST_E2E_001',
    15000.0,
    'Medicamentos',
    'Producto de prueba para tests E2E del sistema MediSupply',
    true,
    'Unidad',
    'Refrigerado',
    '7ec13a5e-c1de-4f9a-a1eb-7c2b6d24ee76',
    'Proveedor Test E2E',
    NOW()
)
ON CONFLICT (sku) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    precio_unitario = EXCLUDED.precio_unitario,
    disponible = true;

-- ============================================================================
-- 9. INVENTARIO DE PRUEBA (100 unidades disponibles)
-- ============================================================================
INSERT INTO inventario (
    id,
    producto_id,
    lote,
    cantidad,
    ubicacion,
    temperatura_requerida,
    estado,
    fecha_vencimiento,
    observaciones,
    created_at
)
VALUES (
    'e482bf52-8136-428c-b4b4-f7eb21b5d74e',
    '9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c',
    'LOTE-E2E-001',
    100,
    'Bodega Central - Test',
    '2-8°C',
    'DISPONIBLE',
    '2026-12-31',
    'Inventario de prueba para E2E tests',
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    cantidad = 100,
    estado = 'DISPONIBLE';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- Descomentar para verificar que los datos se insertaron correctamente

SELECT 'Conductores:', COUNT(*) FROM conductores WHERE id = 1;
SELECT 'Vehículos:', COUNT(*) FROM vehiculos WHERE id = 1;
SELECT 'Productos:', COUNT(*) FROM productos WHERE sku = 'TEST_E2E_001';
SELECT 'Inventario:', cantidad FROM inventario WHERE producto_id = '11111111-1111-1111-1111-111111111111';
SELECT 'Clientes:', COUNT(*) FROM clientes_institucionales WHERE nit = '900123456-7';
SELECT 'Vendedores:', COUNT(*) FROM vendedores WHERE email = 'operador@test.com';
SELECT 'Usuarios:', COUNT(*) FROM users WHERE email IN ('cliente@test.com', 'operador@test.com');

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
--
-- 1. PASSWORDS:
--    Los usuarios tienen password: "test123"
--    Ya están hasheados con Argon2
--
-- 2. ORDEN DE INSERCIÓN:
--    El script inserta en el orden correcto respetando foreign keys:
--    plan_venta → vendedores → clientes → users → proveedor → productos → inventario
--
-- 3. LIMPIEZA:
--    Para limpiar los datos de prueba, ejecuta:
--    DELETE FROM inventario WHERE id = '77777777-7777-7777-7777-777777777777';
--    DELETE FROM productos WHERE sku = 'TEST_E2E_001';
--    DELETE FROM proveedores WHERE id = '88888888-8888-8888-8888-888888888888';
--    DELETE FROM users WHERE email IN ('cliente@test.com', 'operador@test.com');
--    DELETE FROM clientes_institucionales WHERE nit = '900123456-7';
--    DELETE FROM vendedores WHERE email = 'operador@test.com';
--    DELETE FROM planes_venta WHERE id = '99999999-9999-9999-9999-999999999999';
--    DELETE FROM vehiculos WHERE id = 1;
--    DELETE FROM conductores WHERE id = 1;
--
-- ============================================================================
