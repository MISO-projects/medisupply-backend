#!/bin/bash

# ============================================================================
# Script para ejecutar pruebas E2E de MediSupply
# ============================================================================
# Este script verifica prerequisitos y ejecuta las pruebas E2E
#
# Uso:
#   ./tests/e2e/run_e2e_tests.sh
#   ./tests/e2e/run_e2e_tests.sh --setup    # Solo verifica servicios
#   ./tests/e2e/run_e2e_tests.sh --verbose  # Output detallado
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

# ============================================================================
# Funciones auxiliares
# ============================================================================

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

check_service() {
    local service_name=$1
    local port=$2

    if nc -z localhost $port 2>/dev/null; then
        print_success "$service_name (puerto $port) está corriendo"
        return 0
    else
        print_error "$service_name (puerto $port) NO está corriendo"
        return 1
    fi
}

# ============================================================================
# Verificación de prerequisitos
# ============================================================================

check_prerequisites() {
    print_header "Verificando Prerequisitos"

    local all_ok=true

    # Python
    if command -v python3 &> /dev/null; then
        print_success "Python 3 instalado: $(python3 --version)"
    else
        print_error "Python 3 no está instalado"
        all_ok=false
    fi

    # pytest
    if python3 -c "import pytest" 2>/dev/null; then
        print_success "pytest instalado"
    else
        print_error "pytest no está instalado"
        print_info "Instala con: pip install pytest pytest-asyncio"
        all_ok=false
    fi

    # httpx
    if python3 -c "import httpx" 2>/dev/null; then
        print_success "httpx instalado"
    else
        print_error "httpx no está instalado"
        print_info "Instala con: pip install httpx"
        all_ok=false
    fi

    # netcat para verificar puertos
    if command -v nc &> /dev/null; then
        print_success "netcat (nc) disponible"
    else
        print_warning "netcat (nc) no disponible - no se verificarán puertos"
    fi

    if [ "$all_ok" = false ]; then
        print_error "Prerequisitos no cumplidos"
        exit 1
    fi
}

# ============================================================================
# Verificación de servicios
# ============================================================================

check_services() {
    print_header "Verificando Servicios"

    local services_ok=true

    # Lista de servicios críticos
    check_service "autenticacion" 3012 || services_ok=false
    check_service "bff-movil" 3014 || services_ok=false
    check_service "bff-web" 3013 || services_ok=false
    check_service "inventario" 3008 || services_ok=false
    check_service "ordenes-command-api" 3000 || services_ok=false
    check_service "ordenes-command-handler" 3001 || services_ok=false
    check_service "ordenes-query-api" 3002 || services_ok=false
    check_service "logistica" 3007 || services_ok=false
    check_service "postgres" 5480 || services_ok=false
    check_service "redis" 6379 || services_ok=false

    if [ "$services_ok" = false ]; then
        print_error "\nAlgunos servicios no están corriendo"
        print_info "Inicia los servicios con: docker-compose up -d"
        exit 1
    fi

    print_success "\nTodos los servicios están corriendo"
}

# ============================================================================
# Verificación de variables de entorno
# ============================================================================

check_environment() {
    print_header "Verificando Configuración"

    local env_file="$SCRIPT_DIR/.env.e2e"

    if [ -f "$env_file" ]; then
        print_success "Archivo .env.e2e encontrado"
        export $(cat "$env_file" | grep -v '^#' | xargs)
    else
        print_warning "Archivo .env.e2e no encontrado"
        print_info "Usando valores por defecto"
        print_info "Copia .env.e2e.example a .env.e2e para personalizar"
    fi
}

# ============================================================================
# Ejecución de pruebas
# ============================================================================

run_tests() {
    print_header "Ejecutando Pruebas E2E"

    cd "$PROJECT_ROOT"

    local pytest_args="-v"

    # Agregar argumentos según flags
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -s"
    fi

    print_info "Comando: pytest tests/e2e/test_pedido_happy_path.py $pytest_args --timeout=60"
    echo ""

    if pytest tests/e2e/test_pedido_happy_path.py $pytest_args --timeout=60; then
        print_header "Resultado"
        print_success "PRUEBAS E2E COMPLETADAS EXITOSAMENTE"
        return 0
    else
        print_header "Resultado"
        print_error "PRUEBAS E2E FALLARON"
        print_info "Revisa los logs arriba para más detalles"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_header "MediSupply - Pruebas E2E"

    # Parsear argumentos
    SETUP_ONLY=false
    VERBOSE=false

    for arg in "$@"; do
        case $arg in
            --setup)
                SETUP_ONLY=true
                ;;
            --verbose)
                VERBOSE=true
                ;;
            --help)
                echo "Uso: $0 [opciones]"
                echo ""
                echo "Opciones:"
                echo "  --setup     Solo verificar prerequisitos y servicios"
                echo "  --verbose   Output detallado durante las pruebas"
                echo "  --help      Mostrar esta ayuda"
                exit 0
                ;;
            *)
                print_error "Opción desconocida: $arg"
                echo "Usa --help para ver opciones disponibles"
                exit 1
                ;;
        esac
    done

    # Ejecutar verificaciones
    check_prerequisites
    check_services
    check_environment

    if [ "$SETUP_ONLY" = true ]; then
        print_success "\nVerificación de setup completada"
        exit 0
    fi

    # Ejecutar pruebas
    if run_tests; then
        exit 0
    else
        exit 1
    fi
}

# Ejecutar main
main "$@"
