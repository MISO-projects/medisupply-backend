# Pruebas de Integración con Newman

Pruebas de integración end-to-end para el backend de MediSupply usando Newman (CLI de Postman).

## Inicio Rápido

### Ejecutar Pruebas Localmente

```bash
# Iniciar todos los servicios y ejecutar pruebas
docker compose -f docker-compose.integration.yml up --build

# Ver resultados
docker compose -f docker-compose.integration.yml logs newman
```

### Limpieza

```bash
docker compose -f docker-compose.integration.yml down -v
```

## Qué se Prueba

La suite de pruebas valida el flujo completo:

1. **Health Checks** - BFF Web y BFF Móvil
2. **Autenticación** - Login y generación de tokens
3. **Configuración de Productos** - Crear proveedor, producto e inventario
4. **Configuración de Ventas** - Crear cliente, plan de ventas y vendedor
5. **Flujo de Órdenes (CQRS)** - Crear y consultar órdenes
6. **Logística** - Crear conductor, vehículo y ruta

## Arquitectura

El entorno de pruebas incluye:
- **Infraestructura**: PostgreSQL, Redis, Emulador de Pub/Sub
- **Microservicios**: 16 servicios (órdenes, productos, inventario, ventas, logística, etc.)
- **Servicios BFF**: Web (puerto 3013) y Móvil (puerto 3014)
- **Ejecutor de Pruebas**: Contenedor Newman

Los servicios inician en orden para asegurar que los topics de Pub/Sub se creen antes de procesar órdenes.

## Usar Imágenes Pre-construidas

Si tienes acceso a GCP:

```bash
# Autenticar
gcloud auth configure-docker us-central1-docker.pkg.dev

# Configurar variables
export GCP_PROJECT_ID=medisupply-474421
export IMAGE_TAG=latest

# Descargar y ejecutar
docker compose -f docker-compose.integration.yml pull
docker compose -f docker-compose.integration.yml up -d --no-build
```

## Solución de Problemas

### Servicios No Inician

```bash
# Verificar estado
docker compose -f docker-compose.integration.yml ps

# Ver logs
docker compose -f docker-compose.integration.yml logs <nombre-servicio>
```

### Errores de Topic No Encontrado

```bash
# Verificar inicialización de Pub/Sub
docker compose -f docker-compose.integration.yml logs pubsub-init
```

Las pruebas de Newman esperan a que la inicialización de Pub/Sub se complete antes de ejecutarse.

## Requisitos

- Docker y Docker Compose
- 8GB+ RAM
- Puertos 3013 y 3014 disponibles
