from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from db.database import Base
from datetime import datetime, timezone
import uuid


class User(Base):
    """
    Modelo de Usuario para autenticación

    Attributes:
        id: Identificador único del usuario (UUID)
        email: Email del usuario (único, usado para login)
        username: Nombre para mostrar del usuario (ej: "Juan Pérez")
        hashed_password: Contraseña hasheada (NUNCA guardamos passwords en texto plano)
        is_active: Indica si el usuario está activo (permite deshabilitar usuarios)
        created_at: Fecha y hora de creación del usuario
        updated_at: Fecha y hora de última actualización
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    role = Column(String, nullable=True, default='seller')
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, email, username, hashed_password, role='seller', is_active=True):
        """
        Constructor del modelo User

        Args:
            email: Email del usuario (único)
            username: Nombre para mostrar
            hashed_password: Contraseña ya hasheada
            is_active: Si el usuario está activo (default: True)
        """
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.role = role

    def to_dict(self):
        """Convierte la instancia de User a diccionario"""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
