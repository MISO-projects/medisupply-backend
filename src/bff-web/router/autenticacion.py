from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from services.autenticacion_service import AutenticacionService, get_autenticacion_service
from services.vendedores_service import VendedoresService, get_vendedores_service
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
    summary="Registrar nuevo vendedor",
    description="Registra un nuevo usuario vendedor en el sistema. El email debe corresponder a un vendedor existente en el sistema de ventas."
)
async def register(
    register_data: RegisterRequest,
    autenticacion_service: AutenticacionService = Depends(get_autenticacion_service),
    vendedores_service: VendedoresService = Depends(get_vendedores_service)
):
    """
    Endpoint para registrar un nuevo usuario vendedor
    
    Flujo:
    1. Verifica que el email exista en el sistema de ventas (vendedores)
    2. Obtiene el ID del vendedor asociado al email
    3. Registra el usuario en el servicio de autenticación con rol 'seller' y el id_vendedor

    Args:
        register_data: Datos de registro (email, username, password)
        autenticacion_service: Servicio de autenticación (inyectado)
        vendedores_service: Servicio de vendedores (inyectado)

    Returns:
        UserResponse: Información del usuario creado

    Raises:
        HTTPException 404: Si el email no existe como vendedor en el sistema
        HTTPException 400: Si el email ya está registrado como usuario
        HTTPException 422: Si hay errores de validación
    """
    try:
        vendedor_response = await vendedores_service.obtener_vendedor_por_email(register_data.email)
        
        if not vendedor_response or 'data' not in vendedor_response:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener la información del vendedor con email {register_data.email}"
            )
        
        id_seller = vendedor_response['data'].get('id')
        if not id_seller:
            raise HTTPException(
                status_code=500,
                detail="El vendedor no tiene un ID válido"
            )
        
        auth_register_data = {
            "email": register_data.email,
            "username": register_data.username,
            "password": register_data.password,
            "role": "seller",
            "id_seller": id_seller
        }
        
        return autenticacion_service.register_user(auth_register_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado durante el registro: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al registrar el usuario: {str(e)}"
        )


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

