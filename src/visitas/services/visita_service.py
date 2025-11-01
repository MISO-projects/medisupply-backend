from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone, date
import logging
import httpx
import os
from sqlalchemy import func, and_, or_, nullslast
import json

from db.database import get_db
from db.visita import Visita
# from schemas.visita_schema import a
from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class VisitaService:
    CACHE_TTL_PROVEEDOR = 3600  # 1 hour for individual provider
    CACHE_TTL_LIST = 300  # 5 minutes for lists
    CACHE_TTL_COUNT = 300  # 5 minutes for counts

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
        self.productos_service_url = os.getenv(
            "PRODUCTOS_SERVICE_URL", "http://productos-service:3000"
        )

    


def get_visita_service(db: Session = Depends(get_db)) -> VisitaService:
    """
    Función de dependencia para obtener una instancia del servicio de visita.
    """
    return VisitaService(db)

