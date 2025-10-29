import os
import jwt
from fastapi import HTTPException, status, Header
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class JWTValidator:
    """Simple JWT validator for extracting user information from tokens"""
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "medisupply-secret-key")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    
    def verify_token(self, token: str) -> dict:
        """
        Verifica y decodifica un token JWT
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            dict: Payload del token decodificado
            
        Raises:
            HTTPException: Si el token es inválido o expiró
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )


# Dependency para obtener el user_id del token JWT
def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extrae el user_id (sub) del token JWT
    
    Args:
        authorization: Header Authorization con formato "Bearer <token>"
        
    Returns:
        str: UUID del usuario autenticado
        
    Raises:
        HTTPException: Si el token no existe, es inválido o expiró
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de token inválido. Use 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = authorization[7:].strip()
        
        # Validar y decodificar token
        validator = JWTValidator()
        payload = validator.verify_token(token)
        
        # Extraer user_id del campo "sub"
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: falta información del usuario"
            )
        
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar token de autorización: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al procesar token de autorización"
        )


# Dependency para obtener el client_id del token JWT
def get_current_client_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extrae el client_id (id_client) del token JWT y valida que el rol sea 'client'
    
    Args:
        authorization: Header Authorization con formato "Bearer <token>"
        
    Returns:
        str: UUID del cliente autenticado
        
    Raises:
        HTTPException: Si el token no existe, es inválido, expiró o no tiene rol de cliente
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de token inválido. Use 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = authorization[7:].strip()
        
        # Validar y decodificar token (sin verificar firma en desarrollo)
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            logger.error(f"Error al decodificar token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token mal formado o inválido"
            )
        
        # Verificar que el rol sea 'client'
        role = payload.get("role")
        if role != "client":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Solo usuarios con rol 'client' pueden crear órdenes"
            )
        
        # Extraer id_client del token
        client_id = payload.get("id_client")
        
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token no contiene id_client"
            )
        
        return client_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar token de autorización: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al procesar token de autorización"
        )

