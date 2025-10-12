# Módulo de Gestión de Proveedores - MediSupply

## 📋 Descripción

Este módulo implementa la funcionalidad completa de gestión de proveedores para MediSupply, permitiendo el registro, actualización, consulta y eliminación de proveedores según los requerimientos de la historia de usuario.

## 🏗️ Arquitectura

### Estructura de Archivos

```
src/proveedores/
├── db/
│   ├── database.py           # Configuración de base de datos
│   └── proveedor_model.py    # Modelo SQLAlchemy
├── schemas/
│   └── proveedor_schema.py   # Schemas Pydantic para validación
├── services/
│   ├── proveedor_service.py  # Lógica de negocio
│   └── health_service.py     # Servicio de salud
├── router/
│   └── proveedor_router.py   # Endpoints REST API
└── main.py                    # Aplicación FastAPI
```

## 📊 Modelo de Datos

### Tabla: `proveedores`

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | UUID | Primary Key | Identificador único |
| `fecha_creacion` | DateTime | Not Null | Fecha de creación |
| `fecha_actualizacion` | DateTime | Not Null | Fecha de última actualización |
| `nombre` | String(255) | Not Null | Nombre del proveedor |
| `id_tributario` | String | Not Null, Unique | RUC/NIT/RFC según país |
| `tipo_proveedor` | String | Not Null | Tipo de proveedor |
| `email` | String | Not Null, Unique | Email del proveedor |
| `pais` | String | Not Null | País de operación |
| `contacto` | String(255) | Nullable | Información de contacto |
| `condiciones_entrega` | String(500) | Nullable | Condiciones de entrega |

## 🔐 Validaciones Implementadas

### 1. **Validación de ID Tributario por País**

- **Perú (RUC)**: 11 dígitos numéricos
- **Colombia (NIT)**: 9-10 dígitos numéricos
- **México (RFC)**: 12-13 caracteres alfanuméricos con formato específico
- **Ecuador (RUC)**: 13 dígitos numéricos

### 2. **Validación de Email**

- Formato válido de email usando `EmailStr` de Pydantic
- Unicidad en el sistema

### 3. **Validación de Campos Obligatorios**

- `nombre`: 1-255 caracteres
- `id_tributario`: Único y con formato válido
- `tipo_proveedor`: Valor de enum predefinido
- `email`: Formato válido y único
- `pais`: Valor de enum predefinido

### 4. **Validación de Longitudes**

- `nombre`: Máximo 255 caracteres
- `contacto`: Máximo 255 caracteres
- `condiciones_entrega`: Máximo 500 caracteres

## 🎯 Endpoints API

### Base URL: `/proveedores`

#### 1. **Crear Proveedor**
```http
POST /proveedores/
```

**Request Body:**
```json
{
  "nombre": "Farmacéutica Nacional S.A.",
  "id_tributario": "20123456789",
  "tipo_proveedor": "Fabricante",
  "email": "contacto@farmaceutica.com",
  "pais": "Perú",
  "contacto": "Juan Pérez - +51 999 888 777",
  "condiciones_entrega": "Entrega en 5 días hábiles, cobertura nacional"
}
```

**Response (201):**
```json
{
  "message": "Creación exitosa",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nombre": "Farmacéutica Nacional S.A.",
    "id_tributario": "20123456789",
    ...
  }
}
```

**Errores:**
- `409`: ID tributario o email ya existe
- `422`: Error de validación en los datos

---

#### 2. **Listar Proveedores**
```http
GET /proveedores/?page=1&page_size=20&pais=Perú&tipo_proveedor=Fabricante
```

**Query Parameters:**
- `page`: Número de página (default: 1)
- `page_size`: Tamaño de página (default: 20, max: 100)
- `pais`: Filtrar por país (opcional)
- `tipo_proveedor`: Filtrar por tipo (opcional)

**Response (200):**
```json
{
  "data": [...],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

#### 3. **Obtener Proveedor por ID**
```http
GET /proveedores/{proveedor_id}
```

**Response (200):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nombre": "Farmacéutica Nacional S.A.",
    ...
  }
}
```

**Errores:**
- `404`: Proveedor no encontrado

---

#### 4. **Actualizar Proveedor**
```http
PUT /proveedores/{proveedor_id}
```

**Request Body (campos opcionales):**
```json
{
  "nombre": "Farmacéutica Nacional S.A.C.",
  "email": "nuevo@farmaceutica.com",
  "contacto": "María García - +51 999 777 888"
}
```

**Response (200):**
```json
{
  "message": "Proveedor actualizado exitosamente",
  "data": {...}
}
```

**Errores:**
- `404`: Proveedor no encontrado
- `409`: Email ya existe en otro proveedor
- `422`: Error de validación

---

#### 5. **Eliminar Proveedor**
```http
DELETE /proveedores/{proveedor_id}
```

**Response (200):**
```json
{
  "message": "Proveedor eliminado exitosamente"
}
```

**Errores:**
- `404`: Proveedor no encontrado

---

## 📝 Enumeraciones

### TipoProveedorEnum
- `Fabricante`
- `Distribuidor`
- `Mayorista`
- `Importador`
- `Minorista`

### PaisEnum
- `Colombia`
- `Perú`
- `Ecuador`
- `México`

### Acceder a la Documentación
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 Testing

### Crear un Proveedor de Prueba

```bash
curl -X POST "http://localhost:8000/proveedores/" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test Farmacéutica",
    "id_tributario": "20123456789",
    "tipo_proveedor": "Fabricante",
    "email": "test@test.com",
    "pais": "Perú",
    "contacto": "Test Contact",
    "condiciones_entrega": "Test conditions"
  }'
```

### Listar Proveedores

```bash
curl "http://localhost:8000/proveedores/?page=1&page_size=10"
```

## 📊 Estructura de Respuestas

### Respuesta Exitosa
```json
{
  "message": "string",
  "data": {...}
}
```

### Respuesta de Error
```json
{
  "detail": "Mensaje de error descriptivo"
}
```

## 🎨 Características Adicionales

### Paginación
- Soporte para paginación en listado de proveedores
- Control de tamaño de página (máximo 100 registros)
- Información de totales y páginas disponibles

### Filtros
- Filtrar por país
- Filtrar por tipo de proveedor
- Combinación de filtros

### Ordenamiento
- Proveedores ordenados por fecha de creación (más recientes primero)

## 📝 Notas Importantes

- Los campos `id_tributario` y `pais` NO se pueden modificar después de la creación
- El email debe ser único en todo el sistema
- Los ID tributarios se validan automáticamente según el país
- Las fechas se manejan en UTC para consistencia
- La base de datos se inicializa automáticamente al iniciar el servicio

