# src/inventario/router/inventario_router.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging
from http import HTTPStatus

# from schemas.visita_schema import (
#     a
# )
from typing import List

from services.visita_service import VisitaService, get_visita_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

visita_router = APIRouter()

