#!/bin/bash

# ============================================================================
# Script de Setup para Pruebas E2E de MediSupply
# ============================================================================
# Este script prepara el ambiente completamente para ejecutar las pruebas E2E
#
# Uso:
#   ./tests/e2e/setup_e2e.sh
# ============================================================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================================================
# PASO 1: Verificar servicios
# ============================================================================

print_header "PASO 1: Verificando Servicios"

if docker compose ps | grep -q "Up"; then
    print_success "Servicios de Docker Compose están corriendo"
else
    print_error "Servicios no están corriendo"
    print_info "Iniciando servicios..."
    docker compose --profile dev up -d
    sleep 5
fi

# ============================================================================
# PASO 2: Limpiar cache de Redis
# ============================================================================

print_header "PASO 2: Limpiando Cache de Redis"

if docker compose exec redis redis-cli FLUSHALL > /dev/null 2>&1; then
    print_success "Cache de Redis limpiado"
else
    print_error "Error al limpiar cache de Redis"
    exit 1
fi

# ============================================================================
# PASO 3: Reiniciar servicio de inventario
# ============================================================================

print_header "PASO 3: Reiniciando Servicio de Inventario"

docker compose restart inventario-service > /dev/null 2>&1
sleep 3
print_success "Servicio de inventario reiniciado"

# ============================================================================
# PASO 4: Ejecutar seed de datos de prueba
# ============================================================================

print_header "PASO 4: Insertando Datos de Prueba"

cd "$PROJECT_ROOT"

if PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db \
    -f "$SCRIPT_DIR/seed_test_data.sql" > /dev/null 2>&1; then
    print_success "Datos de prueba insertados correctamente"
else
    print_warning "Algunos datos ya existen (esto es normal)"
fi

# ============================================================================
# PASO 5: Verificar datos
# ============================================================================

print_header "PASO 5: Verificando Datos de Prueba"

result=$(PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db -t -c \
    "SELECT COUNT(*) FROM users WHERE email IN ('cliente@test.com', 'operador@test.com');")

user_count=$(echo $result | tr -d ' ')

if [ "$user_count" -eq "2" ]; then
    print_success "Usuarios de prueba: $user_count/2"
else
    print_error "Usuarios de prueba: $user_count/2 (se esperaban 2)"
fi

result=$(PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db -t -c \
    "SELECT COUNT(*) FROM productos WHERE sku = 'TEST_E2E_001';")

product_count=$(echo $result | tr -d ' ')

if [ "$product_count" -eq "1" ]; then
    print_success "Producto de prueba: $product_count/1"
else
    print_error "Producto de prueba: $product_count/1 (se esperaba 1)"
fi

result=$(PGPASSWORD=medisupply-pass psql -h localhost -p 5480 -U root -d medisupply-db -t -c \
    "SELECT cantidad FROM inventario WHERE producto_id = '9a44ac77-3fd7-483a-b8a6-ce7c2e0ba85c';")

inventory_count=$(echo $result | tr -d ' ')

if [ ! -z "$inventory_count" ]; then
    print_success "Inventario de prueba: $inventory_count unidades"
else
    print_error "Inventario de prueba no encontrado"
fi

# ============================================================================
# PASO 6: Verificar conectividad de servicios
# ============================================================================

print_header "PASO 6: Verificando Conectividad de Servicios"

services=(
    "autenticacion:3012"
    "bff-movil:3014"
    "bff-web:3013"
    "inventario:3008"
)

all_ok=true

for service in "${services[@]}"; do
    name="${service%:*}"
    port="${service#*:}"

    if nc -z localhost $port 2>/dev/null; then
        print_success "$name (puerto $port)"
    else
        print_error "$name (puerto $port) - NO RESPONDE"
        all_ok=false
    fi
done

# ============================================================================
# Resumen
# ============================================================================

print_header "RESUMEN"

if [ "$all_ok" = true ]; then
    print_success "Setup completado exitosamente"
    echo ""
    print_info "Ahora puedes ejecutar las pruebas E2E:"
    echo ""
    echo "  pytest tests/e2e/test_pedido_happy_path.py -v -s"
    echo ""
    exit 0
else
    print_error "Setup completado con advertencias"
    print_info "Revisa los mensajes anteriores"
    exit 1
fi
