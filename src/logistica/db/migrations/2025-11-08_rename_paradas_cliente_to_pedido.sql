-- Migración: Renombrar columna cliente_id a pedido_id en tabla paradas
-- Paso 1: Renombrar la columna (no destructivo)
ALTER TABLE paradas RENAME COLUMN cliente_id TO pedido_id;

-- Paso 2 (opcional): Convertir a UUID si todos los valores son UUID válidos
-- IMPORTANTE: Validar previamente que no haya cadenas vacías o valores no UUID
-- ALTER TABLE paradas
--   ALTER COLUMN pedido_id TYPE uuid
--   USING NULLIF(pedido_id, '')::uuid;


