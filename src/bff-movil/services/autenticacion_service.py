import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
import logging

logger = logging.getLogger(__name__)


class AutenticacionService:

    def __init__(self):
        self.base_url = os.getenv("AUTENTICACION_SERVICE_URL", "http://autenticacion-service:3000")
        self.timeout = 30.0

    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Autenticacion service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Autenticacion service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Autenticacion health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    def register_user(self, register_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra un nuevo usuario en el sistema

        Args:
            register_data: Datos de registro (email, username, password)

        Returns:
            Dict con información del usuario creado

        Raises:
            HTTPException: Si hay un error en el registro
        """
        try:
            encoded_data = jsonable_encoder(register_data)
            response = httpx.post(
                f"{self.base_url}/auth/register",
                json=encoded_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error registering user: {e}")
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail=e.response.json().get("detail", "Error en el registro"))
            raise HTTPException(status_code=e.response.status_code, detail=f"Error en el servicio de autenticación: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"No se puede conectar al servicio de autenticación: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    def login_user(self, login_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Autentica un usuario y devuelve un token JWT

        Args:
            login_data: Credenciales de login (email, password)

        Returns:
            Dict con el token JWT

        Raises:
            HTTPException: Si las credenciales son inválidas
        """
        try:
            response = httpx.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error during login: {e}")
            if e.response.status_code in [401, 403]:
                raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", "Credenciales inválidas"))
            raise HTTPException(status_code=e.response.status_code, detail=f"Error en el servicio de autenticación: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"No se puede conectar al servicio de autenticación: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    def get_current_user(self, token: str) -> Dict[str, Any]:
        """
        Obtiene la información del usuario actual mediante su token JWT

        Args:
            token: Token JWT del usuario

        Returns:
            Dict con información del usuario

        Raises:
            HTTPException: Si el token es inválido o expiró
        """
        try:
            response = httpx.get(
                f"{self.base_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting current user: {e}")
            if e.response.status_code in [401, 403]:
                raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", "Token inválido o expirado"))
            raise HTTPException(status_code=e.response.status_code, detail=f"Error en el servicio de autenticación: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"No se puede conectar al servicio de autenticación: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting current user: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

def get_autenticacion_service() -> AutenticacionService:
    return AutenticacionService()

