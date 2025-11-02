#!/bin/bash

# Script to run Docker Compose integration tests
# Usage: ./scripts/run_integration_tests.sh [cleanup]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILE="docker-compose.test.yml"
SERVICES_UP=false

# Detect Docker Compose command (V1 vs V2)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}Error: Neither 'docker-compose' nor 'docker compose' is available${NC}"
    exit 1
fi

echo -e "${BLUE}Using Docker Compose command: ${DOCKER_COMPOSE}${NC}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    if [ "$SERVICES_UP" = true ]; then
        echo -e "${YELLOW}Cleaning up Docker Compose services...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" down -v
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Check if cleanup-only was requested
if [ "$1" == "cleanup" ]; then
    echo -e "${YELLOW}Cleaning up existing test services...${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" down -v
    exit 0
fi

# Clean up any existing test services
echo -e "${YELLOW}Cleaning up any existing test services...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# Start services
echo -e "${GREEN}Starting Docker Compose services for integration tests...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

SERVICES_UP=true

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
MAX_WAIT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check if all required services are healthy
    HEALTHY_COUNT=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" ps | grep -c "healthy" || true)
    
    if [ "$HEALTHY_COUNT" -ge 3 ]; then
        # Check both services are responding
        if curl -sf http://localhost:9001/health > /dev/null 2>&1 && \
           curl -sf http://localhost:9002/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ All services are healthy!${NC}"
            break
        fi
    fi
    
    echo -e "${YELLOW}⏳ Waiting for services... (${ELAPSED}s/${MAX_WAIT}s) - Healthy services: ${HEALTHY_COUNT}/3${NC}"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ Services did not become healthy in time${NC}"
    echo -e "${YELLOW}Service status:${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
    echo -e "${YELLOW}Service logs:${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs --tail=50
    exit 1
fi

# Give services a bit more time to fully initialize
echo -e "${YELLOW}Giving services additional time to initialize...${NC}"
sleep 5

# Install test dependencies in the container (if not already installed)
echo -e "${YELLOW}Installing test dependencies in container...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T order-handler-test \
    pip install -q pytest pytest-asyncio httpx

# Run the integration tests INSIDE the order-handler-test container
echo -e "${GREEN}Running integration tests inside order-handler-test container...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Execute pytest inside the container
$DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T order-handler-test \
    python -m pytest tests/integration/test_order_stock_integration.py \
    -v \
    --tb=short \
    --asyncio-mode=auto \
    --color=yes

TEST_EXIT_CODE=$?

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests passed!${NC}"
else
    echo -e "${RED}❌ Integration tests failed${NC}"
    echo -e "${YELLOW}Showing recent logs from services:${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs --tail=100 order-handler-test inventario-test
fi

exit $TEST_EXIT_CODE
