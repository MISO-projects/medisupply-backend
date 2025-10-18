from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from services.autenticacion_service import AutenticacionService, get_autenticacion_service
from schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse, UserResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

autenticacion_router = APIRouter()

# Configurar esquema de seguridad Bearer (para tokens JWT)
security = HTTPBearer()


@autenticacion_router.get("/health")
def health_check(autenticacion_service: AutenticacionService = Depends(get_autenticacion_service)):
    return autenticacion_service.health_check()


@autenticacion_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Registra un nuevo usuario en el sistema con email, nombre de usuario y contraseña"
)
def register(
    register_data: RegisterRequest,
    autenticacion_service: AutenticacionService = Depends(get_autenticacion_service)
):
    """
    Endpoint para registrar un nuevo usuario

    Args:
        register_data: Datos de registro (email, username, password)
        autenticacion_service: Servicio de autenticación (inyectado)

    Returns:
        UserResponse: Información del usuario creado

    Raises:
        HTTPException 400: Si el email ya está registrado
    """
    return autenticacion_service.register_user(register_data.model_dump())


@autenticacion_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description="Autentica un usuario y devuelve un token JWT de acceso"
)
def login(
    login_data: LoginRequest,
    autenticacion_service: AutenticacionService = Depends(get_autenticacion_service)
):
    """
    Endpoint para iniciar sesión

    Args:
        login_data: Credenciales de login (email, password)
        autenticacion_service: Servicio de autenticación (inyectado)

    Returns:
        TokenResponse: Token JWT de acceso

    Raises:
        HTTPException 401: Si las credenciales son inválidas
        HTTPException 403: Si el usuario está inactivo
    """
    return autenticacion_service.login_user(login_data.model_dump())


@autenticacion_router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario actual",
    description="Obtiene la información del usuario autenticado mediante el token JWT"
)
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    autenticacion_service: AutenticacionService = Depends(get_autenticacion_service)
):
    """
    Endpoint para obtener información del usuario actual

    Este endpoint está protegido y requiere un token JWT válido en el header:
    Authorization: Bearer <token>

    Args:
        credentials: Credenciales HTTP Bearer (token JWT)
        autenticacion_service: Servicio de autenticación (inyectado)

    Returns:
        UserResponse: Información del usuario autenticado

    Raises:
        HTTPException 401: Si el token es inválido o expiró
        HTTPException 403: Si el usuario está inactivo
    """
    token = credentials.credentials
    return autenticacion_service.get_current_user(token)

