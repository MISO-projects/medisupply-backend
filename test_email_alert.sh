#!/bin/bash

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Iniciando prueba de envío de correo de alerta...${NC}"

# 1. Generar ID aleatorio para simular producto/inventario
UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
USER_UUID="550e8400-e29b-41d4-a716-446655440000"

echo -e "${GREEN}📝 1. Disparando alerta por ELIMINACION_SOSPECHOSA (>100 unidades)...${NC}"

# Enviamos evento que cumpla con UMBRAL_CANTIDAD_ELIMINACION > 100
curl -X POST http://localhost:3011/api/auditoria/eventos/inventario \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "INVENTARIO_ELIMINADO",
    "operation": "ELIMINAR",
    "inventario_id": "'$UUID'",
    "producto_id": "'$UUID'",
    "usuario_id": "'$USER_UUID'",
    "ip_origen": "127.0.0.1",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "datos": {
        "cantidad": 500,
        "motivo": "Prueba de auditoría"
    },
    "cambios": {
        "cantidad_anterior": 500,
        "cantidad_nueva": 0
    }
}'

echo -e "\n\n${GREEN}✅ Solicitud enviada. Verifica los logs del contenedor auditoria-service:${NC}"
echo "docker logs medisupply-backend-auditoria-service-1 | tail -n 50"

