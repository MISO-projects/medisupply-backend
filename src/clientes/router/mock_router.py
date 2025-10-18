
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db, Base, engine
from services.mock_data_service import MockDataService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mock", tags=["mock-data"])


def get_mock_service(db: Session = Depends(get_db)) -> MockDataService:
    return MockDataService(db=db)


@router.post(
    "/init-db",
    summary="Inicializar base de datos",
    description="Crea las tablas necesarias en la base de datos"
)
async def init_database():
    try:
        logger.info("Creando tablas en la base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas exitosamente")
        
        return {
            "success": True,
            "message": "Base de datos inicializada correctamente",
            "tablas_creadas": list(Base.metadata.tables.keys())
        }
    except Exception as e:
        logger.error(f"Error al inicializar base de datos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al inicializar base de datos: {str(e)}"
        )


@router.post(
    "/clientes",
    summary="Crear datos mock de clientes",
    description="Crea clientes de ejemplo en la base de datos para desarrollo/testing"
)
async def create_mock_clientes(
    clear_existing: bool = Query(
        False, 
        description="Si es true, elimina todos los clientes existentes antes de crear los nuevos"
    ),
    mock_service: MockDataService = Depends(get_mock_service)
):
    try:
        logger.info(f"Creando datos mock (clear_existing={clear_existing})...")
        result = mock_service.create_mock_data(clear_existing=clear_existing)
        logger.info(f"Datos mock creados: {result['estadisticas']}")
        return result
        
    except Exception as e:
        logger.error(f"Error al crear datos mock: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete(
    "/clientes",
    summary="Eliminar todos los clientes",
    description="Elimina todos los clientes de la base de datos"
)
async def clear_all_clientes(
    mock_service: MockDataService = Depends(get_mock_service)
):
    try:
        logger.warning("Eliminando todos los clientes de la base de datos...")
        result = mock_service.clear_all_data()
        logger.info(f"Clientes eliminados: {result['clientes_eliminados']}")
        return result
        
    except Exception as e:
        logger.error(f"Error al eliminar datos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/stats",
    summary="Obtener estadísticas de la base de datos",
    description="Retorna información sobre los datos en la base de datos"
)
async def get_database_stats(
    mock_service: MockDataService = Depends(get_mock_service)
):
    try:
        stats = mock_service.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/vendedores",
    summary="Obtener IDs de vendedores mock",
    description="Retorna la lista de IDs de vendedores disponibles para testing"
)
async def get_mock_vendedores(
    mock_service: MockDataService = Depends(get_mock_service)
):

    vendedor_ids = mock_service.get_mock_vendedor_ids()
    
    return {
        "vendedores": [
            {
                "numero": 1,
                "id": vendedor_ids[0],
                "descripcion": "Vendedor con 3 clientes asignados"
            },
            {
                "numero": 2,
                "id": vendedor_ids[1],
                "descripcion": "Vendedor con 2 clientes asignados"
            },
            {
                "numero": 3,
                "id": vendedor_ids[2],
                "descripcion": "Vendedor con 2 clientes asignados"
            }
        ],
        "ejemplo_uso": {
            "descripcion": "Usa estos IDs en el header Authorization",
            "header": "Authorization: Bearer {vendedor_id}",
            "ejemplo_curl": f"curl -H 'Authorization: Bearer {vendedor_ids[0]}' http://localhost:3010/api/clientes/asignados"
        }
    }


@router.post(
    "/clientes/generate/{vendedor_id}",
    summary="Generar clientes para un vendedor específico",
    description="Genera clientes aleatorios y los asigna a un vendedor específico"
)
async def generate_clientes_for_vendedor(
    vendedor_id: str,
    cantidad: int = Query(
        5,
        ge=1,
        le=50,
        description="Cantidad de clientes a generar (entre 1 y 50)"
    ),
    mock_service: MockDataService = Depends(get_mock_service)
):
    try:
        logger.info(f"Generando {cantidad} clientes para vendedor {vendedor_id}...")
        result = mock_service.generate_clientes_for_vendedor(vendedor_id, cantidad)
        logger.info(f"Clientes generados exitosamente: {result['clientes_generados']}")
        return result
        
    except Exception as e:
        logger.error(f"Error al generar clientes: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

