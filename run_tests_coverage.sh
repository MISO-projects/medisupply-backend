#!/bin/bash

# Script para ejecutar tests unitarios con reporte de cobertura en todos los servicios
# Uso: ./run_tests_coverage.sh [--html] [--service=NOMBRE_SERVICIO]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
GENERATE_HTML=false
SPECIFIC_SERVICE=""
FAILED_SERVICES=()
PASSED_SERVICES=()
SKIPPED_SERVICES=()

# Procesar argumentos
for arg in "$@"; do
    case $arg in
        --html)
            GENERATE_HTML=true
            shift
            ;;
        --service=*)
            SPECIFIC_SERVICE="${arg#*=}"
            shift
            ;;
        -h|--help)
            echo "Uso: ./run_tests_coverage.sh [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --html              Genera reporte HTML además del reporte de consola"
            echo "  --service=NOMBRE    Ejecuta tests solo para el servicio especificado"
            echo "  -h, --help          Muestra esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  ./run_tests_coverage.sh                    # Ejecuta todos los tests"
            echo "  ./run_tests_coverage.sh --html             # Ejecuta todos los tests con reporte HTML"
            echo "  ./run_tests_coverage.sh --service=autenticacion  # Solo ejecuta tests de autenticacion"
            exit 0
            ;;
    esac
done

# Directorio base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$BASE_DIR/src"

# Lista de servicios
SERVICES=(
    "auditoria"
    "autenticacion"
    "bff-movil"
    "bff-web"
    "clientes"
    "inventario"
    "logistica"
    "productos"
    "proveedores"
    "reportes"
    "ventas"
)

# Función para ejecutar tests de un servicio
run_service_tests() {
    local service=$1
    local service_path="$SRC_DIR/$service"

    # Verificar si el servicio existe
    if [ ! -d "$service_path" ]; then
        echo -e "${RED}✗${NC} Servicio '$service' no encontrado"
        SKIPPED_SERVICES+=("$service (no encontrado)")
        return 1
    fi

    # Verificar si tiene directorio de tests
    if [ ! -d "$service_path/tests" ]; then
        echo -e "${YELLOW}⊘${NC} $service - No tiene directorio de tests, omitiendo..."
        SKIPPED_SERVICES+=("$service (sin tests)")
        return 0
    fi

    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Ejecutando tests para: $service${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

    cd "$service_path"

    # Construir comando de pytest
    local pytest_cmd="pytest --cov=. --cov-report=term-missing"

    if [ "$GENERATE_HTML" = true ]; then
        pytest_cmd="$pytest_cmd --cov-report=html"
    fi

    # Ejecutar tests
    if $pytest_cmd; then
        echo -e "\n${GREEN}✓${NC} $service - Tests pasaron exitosamente"
        PASSED_SERVICES+=("$service")

        if [ "$GENERATE_HTML" = true ]; then
            echo -e "${GREEN}  Reporte HTML generado en: $service_path/htmlcov/index.html${NC}"
        fi
    else
        echo -e "\n${RED}✗${NC} $service - Tests fallaron"
        FAILED_SERVICES+=("$service")
        cd "$BASE_DIR"
        return 1
    fi

    cd "$BASE_DIR"
    return 0
}

# Banner inicial
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        EJECUTANDO TESTS CON REPORTE DE COBERTURA              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Ejecutar tests
if [ -n "$SPECIFIC_SERVICE" ]; then
    # Ejecutar solo un servicio específico
    echo -e "Ejecutando tests solo para: ${YELLOW}$SPECIFIC_SERVICE${NC}\n"
    run_service_tests "$SPECIFIC_SERVICE"
else
    # Ejecutar todos los servicios
    echo -e "Ejecutando tests para todos los servicios...\n"

    for service in "${SERVICES[@]}"; do
        run_service_tests "$service" || true
    done
fi

# Resumen final
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      RESUMEN FINAL${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

echo -e "${GREEN}✓ Servicios exitosos: ${#PASSED_SERVICES[@]}${NC}"
if [ ${#PASSED_SERVICES[@]} -gt 0 ]; then
    for service in "${PASSED_SERVICES[@]}"; do
        echo -e "  - $service"
    done
fi

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "\n${RED}✗ Servicios fallidos: ${#FAILED_SERVICES[@]}${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "  - $service"
    done
fi

if [ ${#SKIPPED_SERVICES[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}⊘ Servicios omitidos: ${#SKIPPED_SERVICES[@]}${NC}"
    for service in "${SKIPPED_SERVICES[@]}"; do
        echo -e "  - $service"
    done
fi

echo ""

# Código de salida
if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "${RED}Algunos tests fallaron. Revisa los errores anteriores.${NC}\n"
    exit 1
else
    echo -e "${GREEN}¡Todos los tests pasaron exitosamente!${NC}\n"
    exit 0
fi
