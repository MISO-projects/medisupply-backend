import os
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from models.user_model import User
from schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse, UserResponse


class AuthService:
    """
    Servicio de autenticación para gestionar usuarios y tokens JWT

    Responsabilidades:
    - Hash y verificación de contraseñas con Argon2
    - Generación y verificación de tokens JWT
    - Registro de nuevos usuarios
    - Autenticación de usuarios (login)
    """

    def __init__(self):
        # Configurar pwdlib con Argon2 (algoritmo más seguro)
        self.password_hash = PasswordHash((Argon2Hasher(),))

        # Configuración JWT desde variables de entorno
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "medisupply-secret-key")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

    def hash_password(self, password: str) -> str:
        """
        Hashea una contraseña usando Argon2

        Args:
            password: Contraseña en texto plano

        Returns:
            str: Contraseña hasheada
        """
        return self.password_hash.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifica si una contraseña coincide con su hash

        Args:
            plain_password: Contraseña en texto plano
            hashed_password: Contraseña hasheada

        Returns:
            bool: True si coinciden, False si no
        """
        return self.password_hash.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, email: str) -> str:
        """
        Crea un token JWT para el usuario

        Args:
            user_id: UUID del usuario
            email: Email del usuario

        Returns:
            str: Token JWT
        """
        # Calcular tiempo de expiración
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.jwt_expiration_minutes)

        # Payload del JWT
        payload = {
            "sub": user_id,  # "subject" - identificador del usuario
            "email": email,
            "exp": expire,  # Expiration time
            "iat": datetime.now(timezone.utc)  # Issued at
        }

        # Generar token
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token

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
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

    def register_user(self, db: Session, register_data: RegisterRequest) -> UserResponse:
        """
        Registra un nuevo usuario en el sistema

        Args:
            db: Sesión de base de datos
            register_data: Datos de registro del usuario

        Returns:
            UserResponse: Información del usuario creado

        Raises:
            HTTPException: Si el email ya está registrado
        """
        # Hashear la contraseña
        hashed_password = self.hash_password(register_data.password)

        # Crear nuevo usuario
        new_user = User(
            email=register_data.email,
            username=register_data.username,
            hashed_password=hashed_password,
            is_active=True
        )

        try:
            # Guardar en base de datos
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            # Convertir a UserResponse
            user_dict = new_user.to_dict()
            return UserResponse(**user_dict)

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )

    def authenticate_user(self, db: Session, login_data: LoginRequest) -> TokenResponse:
        """
        Autentica un usuario y genera un token JWT

        Args:
            db: Sesión de base de datos
            login_data: Credenciales de login

        Returns:
            TokenResponse: Token JWT de acceso

        Raises:
            HTTPException: Si las credenciales son inválidas
        """
        # Buscar usuario por email
        user = db.query(User).filter(User.email == login_data.email).first()

        # Verificar que existe y está activo
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        # Verificar contraseña
        if not self.verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        # Generar token JWT
        access_token = self.create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        return TokenResponse(access_token=access_token, token_type="bearer")

    def get_current_user(self, db: Session, token: str) -> UserResponse:
        """
        Obtiene el usuario actual desde un token JWT

        Args:
            db: Sesión de base de datos
            token: Token JWT

        Returns:
            UserResponse: Información del usuario

        Raises:
            HTTPException: Si el token es inválido o el usuario no existe
        """
        # Verificar y decodificar token
        payload = self.verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        # Buscar usuario
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        # Convertir a UserResponse
        user_dict = user.to_dict()
        return UserResponse(**user_dict)


# Dependency injection para FastAPI
def get_auth_service() -> AuthService:
    """
    Función de dependencia para inyectar el servicio de autenticación

    Returns:
        AuthService: Instancia del servicio de autenticación
    """
    return AuthService()
