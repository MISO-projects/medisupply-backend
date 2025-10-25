# Configuración de Pub/Sub Emulador

## Inicio Rápido

1. Edita `scripts/pubsub-config.json`
2. Agrega tus topics y suscripciones
3. Reinicia: `docker-compose --profile ordenes restart pubsub-init`

¡Listo! ✨

## Estructura del Archivo de Configuración

```json
{
  "topics": [
    "create-order-command",
    "order-created"
  ],
  "subscriptions": [
    {
      "name": "create-order-command-sub",
      "topic": "create-order-command",
      "pushEndpoint": "order-command-handler:3000",
      "ackDeadlineSeconds": 60
    }
  ],
  "healthChecks": [
    {
      "service": "order-command-handler",
      "endpoint": "order-command-handler:3000/health"
    }
  ]
}
```

## Cómo Agregar un Nuevo Flujo

### Ejemplo: Agregar Inventario

```json
{
  "topics": [
    "create-order-command",
    "order-created",
    "inventory-updated"       ← Nuevo topic
  ],
  "subscriptions": [
    {
      "name": "create-order-command-sub",
      "topic": "create-order-command",
      "pushEndpoint": "order-command-handler:3000",
      "ackDeadlineSeconds": 60
    },
    {
      "name": "inventory-updated-sub",    ← Nueva suscripción
      "topic": "inventory-updated",
      "pushEndpoint": "inventory-handler:3000",
      "ackDeadlineSeconds": 60
    }
  ]
}
```

Luego reinicia:
```bash
docker-compose --profile ordenes restart pubsub-init
```

## Campos del JSON

### Subscription (Suscripción)
- **name**: Nombre único de la suscripción
- **topic**: Topic al que se suscribe (debe existir en el array `topics`)
- **pushEndpoint**: Endpoint del servicio sin `http://` (formato: `servicio:puerto`)
- **ackDeadlineSeconds**: Tiempo límite de confirmación (opcional, default: 60)

### Health Check (Opcional)
- **service**: Nombre del servicio para mostrar
- **endpoint**: URL del health check sin `http://` (formato: `servicio:puerto/path`)

## Múltiples Suscriptores al Mismo Topic

```json
{
  "subscriptions": [
    {
      "name": "audit-sub",
      "topic": "order-created",
      "pushEndpoint": "audit-service:3000"
    },
    {
      "name": "notification-sub",
      "topic": "order-created",
      "pushEndpoint": "notification-service:3000"
    }
  ]
}
```

## Verificación

```bash
# Ver el flujo configurado
docker-compose --profile ordenes logs pubsub-init | grep "Event flow"

# Validar el JSON
jq . scripts/pubsub-config.json

# Ver los topics
docker-compose --profile ordenes exec -T pubsub-emulator sh -c \
  "curl -s http://localhost:8085/v1/projects/medisupply-474421/topics" | jq
```

## Solución de Problemas

### El JSON no es válido
```bash
jq . scripts/pubsub-config.json
```

### Los topics no se crean
```bash
docker-compose --profile ordenes logs pubsub-init
docker-compose --profile ordenes ps pubsub-emulator
```

### El servicio no recibe mensajes

1. Verifica que la suscripción existe:
   ```bash
   docker-compose --profile ordenes logs pubsub-init | grep "Subscription"
   ```

2. El formato del `pushEndpoint` debe ser: `servicio:puerto` (sin `http://`)

3. El servicio debe tener un endpoint POST en `/`

## Ejemplo Completo

```json
{
  "project_id": "medisupply-474421",
  "emulator_host": "pubsub-emulator:8085",
  "topics": [
    "create-order-command",
    "order-created",
    "payment-processed"
  ],
  "subscriptions": [
    {
      "name": "create-order-command-sub",
      "topic": "create-order-command",
      "pushEndpoint": "order-command-handler:3000",
      "ackDeadlineSeconds": 60
    },
    {
      "name": "order-created-sub",
      "topic": "order-created",
      "pushEndpoint": "order-query-projection:3000",
      "ackDeadlineSeconds": 60
    },
    {
      "name": "payment-sub",
      "topic": "payment-processed",
      "pushEndpoint": "payment-handler:3000",
      "ackDeadlineSeconds": 120
    }
  ],
  "healthChecks": [
    {
      "service": "order-command-handler",
      "endpoint": "order-command-handler:3000/health"
    },
    {
      "service": "order-query-projection",
      "endpoint": "order-query-projection:3000/health"
    }
  ]
}
```

## Variables de Entorno

Puedes sobrescribir valores del JSON con variables de entorno:

```yaml
# docker-compose.yml
environment:
  - PUBSUB_PROJECT_ID=otro-proyecto        # Sobrescribe project_id
  - PUBSUB_EMULATOR_HOST=otro-host:8085    # Sobrescribe emulator_host
  - PUBSUB_CONFIG_FILE=/ruta/custom.json   # Usa otro archivo
```

## Resumen

**Para agregar un nuevo flujo de Pub/Sub:**

1. Abre `scripts/pubsub-config.json`
2. Agrega el nombre del topic al array `topics`
3. Agrega el objeto de suscripción al array `subscriptions`
4. Guarda y reinicia: `docker-compose --profile ordenes restart pubsub-init`

