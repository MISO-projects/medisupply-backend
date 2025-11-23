# Pruebas de Carga K6 - MediSupply

Scripts de k6 para pruebas de carga del backend de MediSupply.

## Scripts Disponibles

- **`create-orders.js`** - Prueba de creación de órdenes (7 req/s)
- **`query-orders.js`** - Prueba de consulta de órdenes (7 req/s)

## Variables de Entorno

| Variable | Descripción | Por Defecto |
|----------|-------------|-------------|
| `BFF_WEB_URL` | URL del BFF Web | `http://localhost:3013` |
| `BFF_MOVIL_URL` | URL del BFF Móvil | `http://localhost:3014` |
| `EMAIL` | Email para autenticación | `alejo@mail.com` |
| `PASSWORD` | Contraseña | `Password123!` |

## Uso Rápido

### Ambiente Local (por defecto)
```bash
k6 run k6/create-orders.js
k6 run k6/query-orders.js
```

### Ambiente Remoto (Staging/Producción)
```bash
# Opción 1: Variables en línea
k6 run -e BFF_WEB_URL=https://medisupply.tech/web \
       -e BFF_MOVIL_URL=https://medisupply.tech/movil \
       -e EMAIL=alejo@mail.com \
       -e PASSWORD=Password123! \
       k6/create-orders.js

# Opción 2: Exportar variables
export BFF_WEB_URL=https://medisupply.tech/web
export BFF_MOVIL_URL=https://medisupply.tech/movil
export EMAIL=alejo@mail.com
export PASSWORD=Password123!

k6 run k6/create-orders.js
```

## Características

### create-orders.js
- ✅ Obtiene datos dinámicos (clientes, vendedores, productos)
- ✅ Genera órdenes aleatorias con datos reales
- ✅ Solo usa productos disponibles en inventario
- ✅ Autenticación JWT automática

### query-orders.js
- ✅ Obtiene IDs de órdenes dinámicamente
- ✅ Consulta órdenes aleatorias
- ✅ Autenticación JWT automática

## Umbrales de Rendimiento

**create-orders.js:**
- p95 < 2000ms, p99 < 3000ms, promedio < 1000ms
- Tasa de fallo < 1%

**query-orders.js:**
- p95 < 1000ms, p99 < 2000ms, promedio < 500ms
