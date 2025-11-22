# Newman Integration Tests

This document describes how to run the Newman integration tests for the MediSupply backend using the `docker-compose.integration.yml` file.

## Overview

The integration test suite uses Newman (Postman's CLI runner) to execute end-to-end tests against all microservices in the MediSupply architecture. The tests validate the complete flow from authentication through order creation and logistics.

## Architecture

The test environment includes:
- **Infrastructure**: PostgreSQL, Redis, Pub/Sub Emulator, Pub/Sub Initialization
- **Orders (CQRS)**: Command API, Command Handler, Query API, Query Projection
- **Core Services**: Productos, Proveedores, Inventario, Ventas, Clientes, Logística, Autenticación
- **Supporting Services**: Reportes, Auditoría, Visitas
- **BFF Services**: BFF Web, BFF Móvil
- **Test Runner**: Newman container

### Startup Sequence

The services start in a specific order to ensure proper initialization:

1. **Infrastructure Layer**: PostgreSQL, Redis, Pub/Sub Emulator start first
2. **Pub/Sub Initialization**: Creates topics and subscriptions (waits for emulator + handlers)
3. **Microservices**: All application services start in parallel
4. **BFF Services**: Start after all dependencies are healthy
5. **Newman Tests**: Run only after BFFs are healthy AND Pub/Sub is fully initialized

This sequence is critical because the order creation flow requires Pub/Sub topics to exist before the first order is created.

## Running Tests Locally

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB of available RAM
- Ports 3013 and 3014 available

### Option 1: Build from Source (Default)

This is the recommended approach for local development:

```bash
# Start all services and run tests
docker compose -f docker-compose.integration.yml up --build

# Or run in detached mode and view newman logs
docker compose -f docker-compose.integration.yml up -d --build
docker compose -f docker-compose.integration.yml logs -f newman
```

### Option 2: Use Pre-built Images from Artifact Registry

If you have access to the GCP Artifact Registry:

```bash
# Authenticate with GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# Set environment variables
export GCP_PROJECT_ID=medisupply-474421
export IMAGE_TAG=latest

# Pull images and start services
docker compose -f docker-compose.integration.yml pull
docker compose -f docker-compose.integration.yml up -d --no-build

# View newman logs
docker compose -f docker-compose.integration.yml logs -f newman
```

### Cleanup

```bash
# Stop and remove all containers and volumes
docker compose -f docker-compose.integration.yml down -v

# Optional: Remove images
docker compose -f docker-compose.integration.yml down -v --rmi all
```

## Running Tests in GitHub Actions

### Automatic Trigger (Pull Requests)

The tests automatically run on pull requests to `main`:
- **Image Source**: Builds from source (no GCP auth needed)
- **Image Tag**: `pr-{number}` (e.g., `pr-123`)
- **Purpose**: Validate changes before merging

### Manual Trigger

The tests can also be triggered manually via GitHub Actions:

1. Go to **Actions** tab in the repository
2. Select **Newman Integration Tests** workflow
3. Click **Run workflow**
4. Choose options:
   - **Use pre-built images**: `true` (default) or `false`
   - **Image tag**: `latest` (default), commit SHA, or branch name
5. Click **Run workflow**

### Workflow Inputs (Manual Trigger Only)

- **use_prebuilt_images** (boolean, default: `true`):
  - `true`: Pull images from Artifact Registry (faster, requires GCP auth)
  - `false`: Build images from source (slower, no GCP required)

- **image_tag** (string, default: `latest`):
  - Specify which image tag to test
  - Examples: `latest`, `main`, commit SHA

### Viewing Results

After the workflow completes:
1. Check the workflow run summary for pass/fail status
2. Download the Newman test results artifact (named `newman-test-results-{tag}-{run_number}`)
3. View detailed logs for any failures

### Disabling PR Tests (Temporary)

If you need to temporarily disable tests on pull requests:

1. Edit `.github/workflows/newman-integration-tests.yml`
2. Comment out or remove the `pull_request:` trigger:
   ```yaml
   on:
     # pull_request:
     #   branches: [ main ]
     workflow_dispatch:
       # ... inputs
   ```
3. Commit and push the change

## Test Collection

The test suite (`collection/medisupply-tests.postman_collection.json`) includes:

1. **Health Checks**
   - BFF Web health endpoint
   - BFF Móvil health endpoint

2. **Authentication Flow**
   - Login as seller
   - Token generation and storage

3. **Supplier & Product Setup**
   - Create supplier (proveedor)
   - Create product (producto)
   - Create inventory (inventario)

4. **Sales Setup**
   - Create client (cliente)
   - Create sales plan (plan de ventas)
   - Create seller (vendedor)

5. **Order Flow (CQRS)**
   - Create order via Command API
   - Wait for projection sync (10 seconds)
   - Query order via Query API
   - Validate associations (client, seller, products)

6. **Logistics Flow**
   - Create driver (conductor)
   - Create vehicle (vehículo)
   - Create route (ruta) with order
   - Query route and validate associations

## Environment Variables

The following environment variables can be customized:

### For docker-compose.integration.yml

```bash
# GCP Configuration (for pre-built images)
GCP_PROJECT_ID=medisupply-474421
GCP_REGISTRY=us-central1-docker.pkg.dev
IMAGE_TAG=latest

# Database Configuration (default values)
POSTGRES_DB=medisupply-db
POSTGRES_USER=root
POSTGRES_PASSWORD=medisupply-pass

# Pub/Sub Configuration
PUBSUB_PROJECT_ID=medisupply-474421
```

### For GitHub Workflow

Set these as repository secrets:
- `GCP_PROJECT_ID`: Your GCP project ID
- `WIF_PROVIDER`: Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT`: Service account for authentication

## Troubleshooting

### Services Not Becoming Healthy

If services fail to become healthy:

```bash
# Check service status
docker compose -f docker-compose.integration.yml ps

# View logs for specific service
docker compose -f docker-compose.integration.yml logs <service-name>

# Common services to check:
docker compose -f docker-compose.integration.yml logs pg_db
docker compose -f docker-compose.integration.yml logs pubsub-emulator
docker compose -f docker-compose.integration.yml logs pubsub-init
docker compose -f docker-compose.integration.yml logs bff-web
docker compose -f docker-compose.integration.yml logs bff-movil
```

### Pub/Sub Topic Not Found Errors

If you see "404 Topic not found" errors in order-command-api:

```bash
# Check if pubsub-init completed successfully
docker compose -f docker-compose.integration.yml logs pubsub-init

# Verify topics were created
docker compose -f docker-compose.integration.yml exec pubsub-emulator \
  curl -s http://localhost:8085/v1/projects/medisupply-474421/topics

# Restart pubsub-init if needed
docker compose -f docker-compose.integration.yml restart pubsub-init
```

The Newman tests will wait for `pubsub-init` to complete its health check before starting, ensuring all topics and subscriptions are created.

### Newman Tests Failing

```bash
# View newman logs
docker compose -f docker-compose.integration.yml logs newman

# Run newman interactively for debugging
docker compose -f docker-compose.integration.yml run --rm newman
```

### Port Conflicts

If ports 3013 or 3014 are already in use:

```bash
# Find what's using the ports
lsof -i :3013
lsof -i :3014

# Stop conflicting services or modify ports in docker-compose.integration.yml
```

### Memory Issues

If you encounter out-of-memory errors:

```bash
# Check Docker memory allocation
docker system df

# Increase Docker Desktop memory limit (recommended: 8GB+)
# Docker Desktop → Settings → Resources → Memory
```

## Performance Tips

### Faster Startup Times

1. **Use pre-built images**: Pull from Artifact Registry instead of building
2. **Keep infrastructure running**: Only restart application services
3. **Use BuildKit**: Enabled by default in the compose file

### Parallel Builds

```bash
# Build images in parallel
COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 \
  docker compose -f docker-compose.integration.yml build --parallel
```

## CI/CD Integration

### Integration with Deployment Pipeline

You can integrate these tests into your deployment pipeline:

```yaml
# Example: Run after successful deployment
- name: Run Integration Tests
  uses: ./.github/workflows/newman-integration-tests.yml
  with:
    use_prebuilt_images: true
    image_tag: ${{ github.sha }}
```

### Scheduled Runs

Add a schedule trigger to run tests periodically:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  workflow_dispatch:
    # ... existing inputs
```

## Development Workflow

### Testing Local Changes

1. Make changes to a microservice
2. Rebuild only that service:
   ```bash
   docker compose -f docker-compose.integration.yml build <service-name>
   ```
3. Restart the service:
   ```bash
   docker compose -f docker-compose.integration.yml up -d <service-name>
   ```
4. Re-run Newman tests:
   ```bash
   docker compose -f docker-compose.integration.yml run --rm newman
   ```

### Adding New Tests

1. Edit `collection/medisupply-tests.postman_collection.json`
2. Test locally:
   ```bash
   docker compose -f docker-compose.integration.yml up --build
   ```
3. Commit changes and verify in CI

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs for error details
3. Consult the main project README
4. Contact the development team

## Related Documentation

- [Main README](./README.md)
- [Pub/Sub Setup](./scripts/README-PUBSUB.md)
- [Docker Compose Development](./docker-compose.yml)
- [CI/CD Pipeline](./.github/workflows/cd-deploy.yml)

