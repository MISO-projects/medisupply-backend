from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.health_service import HealthService, get_health_service
from router.auditoria import auditoria_router
from router.autenticacion import autenticacion_router
from router.clientes import clientes_router
from router.inventario import inventario_router
from router.logistica import logistica_router
from router.ordenes_commands import ordenes_commands_router
from router.ordenes_queries import ordenes_queries_router
from router.productos import productos_router
from router.proveedores import proveedor_router
from router.reportes import reportes_router
from router.ventas import ventas_router
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply - BFF Web",
    description="Backend for Frontend - API Gateway para MediSupply Web",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/web"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auditoria_router, prefix="/auditoria", tags=["auditoria"])
app.include_router(autenticacion_router, prefix="/autenticacion", tags=["autenticacion"])
app.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
app.include_router(inventario_router, prefix="/inventario", tags=["inventario"])
app.include_router(logistica_router, prefix="/logistica", tags=["logistica"])
app.include_router(ordenes_commands_router, prefix="/ordenes/commands", tags=["ordenes-commands"])
app.include_router(ordenes_queries_router, prefix="/ordenes/queries", tags=["ordenes-queries"])
app.include_router(productos_router, prefix="/productos", tags=["productos"])
app.include_router(proveedor_router, prefix="/proveedores", tags=["proveedores"])
app.include_router(reportes_router, prefix="/reportes", tags=["reportes"])
app.include_router(ventas_router, prefix="/ventas", tags=["ventas"])

@app.get("/health")
def health_check(
    details: bool = False,
    health_service: HealthService = Depends(get_health_service)
):
    health_status = health_service.check_overall_health(include_details=details)
    
    return health_status

