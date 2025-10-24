from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from db.database import get_db
from models.ruta_model import Conductor, Vehiculo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recursos", tags=["recursos"])


@router.get(
    "/conductores",
    summary="Listar todos los conductores",
    description="Obtiene la lista de todos los conductores registrados"
)
def listar_conductores(
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:

    try:
        query = db.query(Conductor)
        
        if activo is not None:
            query = query.filter(Conductor.activo == activo)
        
        conductores = query.all()
        logger.info(f"Se encontraron {len(conductores)} conductores")
        
        return [
            {
                "id": c.id,
                "nombre": c.nombre,
                "apellido": c.apellido,
                "nombre_completo": f"{c.nombre} {c.apellido}",
                "documento": c.documento,
                "telefono": c.telefono,
                "email": c.email,
                "licencia_conducir": c.licencia_conducir,
                "activo": c.activo
            }
            for c in conductores
        ]
    except Exception as e:
        logger.error(f"Error al listar conductores: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al listar conductores: {str(e)}")


@router.get(
    "/conductores/{conductor_id}",
    summary="Obtener conductor por ID",
    description="Obtiene los detalles de un conductor específico"
)
def obtener_conductor(
    conductor_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    try:
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        
        if not conductor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conductor con ID {conductor_id} no encontrado"
            )
        
        return conductor.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener conductor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener conductor: {str(e)}")



@router.get(
    "/vehiculos",
    summary="Listar todos los vehículos",
    description="Obtiene la lista de todos los vehículos registrados"
)
def listar_vehiculos(
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    tipo: str = Query(None, description="Filtrar por tipo de vehículo"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:

    try:
        query = db.query(Vehiculo)
        
        if activo is not None:
            query = query.filter(Vehiculo.activo == activo)
        
        if tipo:
            query = query.filter(Vehiculo.tipo == tipo)
        
        vehiculos = query.all()
        logger.info(f"Se encontraron {len(vehiculos)} vehículos")
        
        return [v.to_dict() for v in vehiculos]
        
    except Exception as e:
        logger.error(f"Error al listar vehículos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al listar vehículos: {str(e)}")


@router.get(
    "/vehiculos/{vehiculo_id}",
    summary="Obtener vehículo por ID",
    description="Obtiene los detalles de un vehículo específico"
)
def obtener_vehiculo(
    vehiculo_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    try:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
        
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehículo con ID {vehiculo_id} no encontrado"
            )
        
        return vehiculo.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener vehículo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener vehículo: {str(e)}")

