
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://autenticacion-service:3000")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{auth_service_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "sub": user_data.get("id"),  # ID del usuario
                    "email": user_data.get("email"),
                    "role": user_data.get("role")
                }
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido o expirado"
                )
            else:
                logger.error(f"Error validando token: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Error al validar el token"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al servicio de autenticación: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de autenticación no disponible"
        )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    if not credentials:
        return {"sub": None, "email": None, "role": None}
    
    try:
        import asyncio
        return asyncio.run(get_current_user(credentials))
    except:
        return {"sub": None, "email": None, "role": None}

