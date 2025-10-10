# Servicio de Clientes - MediSupply

Este servicio maneja la gestión de clientes institucionales y su relación con vendedores en el sistema MediSupply.

## Endpoints Disponibles

### GET /api/clientes/asignados

Obtiene la lista de clientes institucionales asignados al vendedor autenticado.

#### Autenticación
- **Requerido**: Sí
- **Tipo**: Bearer Token
- **Rol**: VENDEDOR

#### Headers
```
Authorization: Bearer <jwt_token>
```

#### Respuesta Exitosa (200)
```json
{
  "clientes": [
    {
      "id": "C001",
      "nombre": "Hospital General",
      "nit": "901234567-8",
      "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
    },
    {
      "id": "C002",
      "nombre": "Clinica San Martin",
      "nit": "901987654-3",
      "logoUrl": "https://storage.googleapis.com/logos/clinica-san-martin.png"
    }
  ],
  "total": 2
}
```

#### Respuestas de Error

**401 - No autorizado**
```json
{
  "detail": "Token de autorización requerido"
}
```

**500 - Error interno**
```json
{
  "detail": "Error interno del servidor al obtener clientes asignados"
}
```

### GET /api/clientes/asignados/{cliente_id}

Obtiene un cliente específico si está asignado al vendedor autenticado.

#### Parámetros
- `cliente_id` (string): ID único del cliente

#### Respuesta Exitosa (200)
```json
{
  "id": "C001",
  "nombre": "Hospital General",
  "nit": "901234567-8",
  "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
}
```

#### Respuestas de Error

**404 - Cliente no encontrado**
```json
{
  "detail": "Cliente C001 no encontrado o no asignado al vendedor"
}
```

## Características Técnicas

### Cache Redis
- Los resultados se cachean en Redis por 5 minutos (300 segundos)
- Clave de cache: `clientes_asignados:{vendedor_id}`
- El cache se invalida automáticamente cuando se actualizan los datos

### Modelos de Datos

#### ClienteInstitucional
```python
{
  "id": "UUID",
  "nombre": "string",
  "nit": "string (único)",
  "logo_url": "string (opcional)",
  "id_vendedor": "UUID (referencia externa)",
  "fecha_creacion": "datetime",
  "fecha_actualizacion": "datetime"
}
```

### Arquitectura de Microservicios
- **Servicio Clientes**: Maneja solo la entidad `ClienteInstitucional`
- **Servicio Vendedores**: Maneja la entidad `Vendedor` (servicio separado)
- **Referencia Externa**: `id_vendedor` es una referencia UUID al servicio de vendedores
- **Sin Relaciones Directas**: No hay relaciones SQLAlchemy entre servicios

## Configuración

### Variables de Entorno
```bash
POSTGRES_USER=root
POSTGRES_PASSWORD=medisupply-pass
POSTGRES_HOST=pg_db
POSTGRES_PORT=5432
POSTGRES_DB=medisupply-db
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Dependencias
- FastAPI
- SQLAlchemy
- Redis
- Pydantic
- PostgreSQL

## Ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
fastapi run main.py --port 8080
```

## Testing

```bash
# Ejecutar pruebas
pytest tests/

# Ejecutar con cobertura
pytest --cov=. tests/
```

## Notas de Implementación

### Autenticación
- Actualmente el endpoint simula la extracción del vendedor_id desde el token
- En producción, debe implementarse la validación real del JWT
- El token debe contener el user_id y verificar el rol VENDEDOR

### Integración con Servicio Vendedores
- **Validación de Vendedor**: El servicio de vendedores debe validar que el `vendedor_id` existe
- **Comunicación**: Los servicios se comunican vía API REST o eventos
- **Independencia**: Cada servicio mantiene su propia base de datos
- **Referencias**: Solo se usan UUIDs como referencias entre servicios

### Cache
- El cache mejora significativamente el rendimiento
- Se maneja automáticamente la desconexión de Redis
- Los errores de cache no afectan la funcionalidad principal

### Logging
- Se registran todas las operaciones importantes
- Los errores se logean con detalles para debugging
- Se incluye información de rendimiento (tiempo de respuesta, cantidad de resultados)
