-- Migraciones para el Sistema de Alertas de Auditoría
-- Base de datos: auditoria_db

-- ============================================
-- Tabla: audit_log
-- Descripción: Registra todas las operaciones de inventario
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    inventario_id UUID,
    producto_id UUID,
    usuario_id UUID,
    ip_origen VARCHAR(45),
    datos_operacion JSONB,
    cambios JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejorar el rendimiento de consultas
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit_log(operation);
CREATE INDEX IF NOT EXISTS idx_audit_log_inventario_id ON audit_log(inventario_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_producto_id ON audit_log(producto_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_usuario_id ON audit_log(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- ============================================
-- Tabla: alertas
-- Descripción: Almacena las alertas de seguridad generadas
-- ============================================
CREATE TABLE IF NOT EXISTS alertas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(100) NOT NULL,
    severidad VARCHAR(20) NOT NULL CHECK (severidad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')),
    mensaje TEXT NOT NULL,
    descripcion_detallada TEXT,
    evento_relacionado JSONB,
    audit_log_id UUID REFERENCES audit_log(id) ON DELETE SET NULL,
    estado VARCHAR(20) DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'REVISADO', 'RESUELTO', 'FALSA_ALARMA')),
    revisado_por UUID,
    notas_revision TEXT,
    notificacion_enviada BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para alertas
CREATE INDEX IF NOT EXISTS idx_alertas_tipo ON alertas(tipo);
CREATE INDEX IF NOT EXISTS idx_alertas_severidad ON alertas(severidad);
CREATE INDEX IF NOT EXISTS idx_alertas_estado ON alertas(estado);
CREATE INDEX IF NOT EXISTS idx_alertas_created_at ON alertas(created_at DESC);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_alertas_updated_at BEFORE UPDATE ON alertas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Tabla: email_notificaciones
-- Descripción: Emails registrados para recibir notificaciones
-- ============================================
CREATE TABLE IF NOT EXISTS email_notificaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    nombre VARCHAR(255),
    cargo VARCHAR(100),
    activo BOOLEAN DEFAULT TRUE,
    severidades_minimas JSONB DEFAULT '["ALTA", "CRITICA"]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para email_notificaciones
CREATE INDEX IF NOT EXISTS idx_email_notificaciones_email ON email_notificaciones(email);
CREATE INDEX IF NOT EXISTS idx_email_notificaciones_activo ON email_notificaciones(activo);

-- Trigger para updated_at en email_notificaciones
CREATE TRIGGER update_email_notificaciones_updated_at BEFORE UPDATE ON email_notificaciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Datos de ejemplo (opcional)
-- ============================================

-- Insertar email de administrador por defecto
INSERT INTO email_notificaciones (email, nombre, cargo, severidades_minimas)
VALUES ('admin@medisupply.com', 'Administrador', 'Administrador del Sistema', '["ALTA", "CRITICA"]'::jsonb)
ON CONFLICT (email) DO NOTHING;

-- ============================================
-- Vistas útiles
-- ============================================

-- Vista: alertas_pendientes
CREATE OR REPLACE VIEW alertas_pendientes AS
SELECT 
    a.*,
    al.operation,
    al.usuario_id,
    al.timestamp as evento_timestamp
FROM alertas a
LEFT JOIN audit_log al ON a.audit_log_id = al.id
WHERE a.estado = 'PENDIENTE'
ORDER BY a.created_at DESC;

-- Vista: estadisticas_alertas_diarias
CREATE OR REPLACE VIEW estadisticas_alertas_diarias AS
SELECT 
    DATE(created_at) as fecha,
    severidad,
    COUNT(*) as cantidad
FROM alertas
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), severidad
ORDER BY fecha DESC, severidad;

-- ============================================
-- Permisos (ajustar según tu configuración)
-- ============================================

-- GRANT SELECT, INSERT, UPDATE ON audit_log TO medisupply_app;
-- GRANT SELECT, INSERT, UPDATE ON alertas TO medisupply_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON email_notificaciones TO medisupply_app;

-- ============================================
-- Verificación
-- ============================================

-- Verificar que las tablas fueron creadas
SELECT 
    table_name, 
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name IN ('audit_log', 'alertas', 'email_notificaciones')
ORDER BY table_name;

-- Verificar índices creados
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND tablename IN ('audit_log', 'alertas', 'email_notificaciones')
ORDER BY tablename, indexname;







