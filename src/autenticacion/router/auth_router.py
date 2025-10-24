from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db.database import get_db
from services.auth_service import AuthService, get_auth_service
from schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse, UserResponse

# Configurar router
router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

# Configurar esquema de seguridad Bearer (para tokens JWT)
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Registra un nuevo usuario en el sistema con email, nombre de usuario y contraseña"
)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint para registrar un nuevo usuario

    Args:
        register_data: Datos de registro (email, username, password)
        db: Sesión de base de datos (inyectada)
        auth_service: Servicio de autenticación (inyectado)

    Returns:
        UserResponse: Información del usuario creado

    Raises:
        HTTPException 400: Si el email ya está registrado
    """
    return auth_service.register_user(db, register_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description="Autentica un usuario y devuelve un token JWT de acceso"
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint para iniciar sesión

    Args:
        login_data: Credenciales de login (email, password)
        db: Sesión de base de datos (inyectada)
        auth_service: Servicio de autenticación (inyectado)

    Returns:
        TokenResponse: Token JWT de acceso

    Raises:
        HTTPException 401: Si las credenciales son inválidas
        HTTPException 403: Si el usuario está inactivo
    """
    return auth_service.authenticate_user(db, login_data)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario actual",
    description="Obtiene la información del usuario autenticado mediante el token JWT"
)
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint para obtener información del usuario actual

    Este endpoint está protegido y requiere un token JWT válido en el header:
    Authorization: Bearer <token>

    Args:
        credentials: Credenciales HTTP Bearer (token JWT)
        db: Sesión de base de datos (inyectada)
        auth_service: Servicio de autenticación (inyectado)

    Returns:
        UserResponse: Información del usuario autenticado

    Raises:
        HTTPException 401: Si el token es inválido o expiró
        HTTPException 403: Si el usuario está inactivo
    """
    token = credentials.credentials
    return auth_service.get_current_user(db, token)


@router.get(
    "/sellers",
    status_code=status.HTTP_200_OK,
    summary="Obtener IDs de vendedores activos",
    description="Devuelve una lista con los IDs de los usuarios con role='seller' y is_active=True. No requiere autenticación."
)
def get_sellers(
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint público para obtener lista de IDs de vendedores activos.
    """
    return auth_service.get_active_seller_ids(db)
