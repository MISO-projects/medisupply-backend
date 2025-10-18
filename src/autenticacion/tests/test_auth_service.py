import pytest
from unittest.mock import Mock
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from services.auth_service import AuthService
from models.user_model import User
from schemas.auth_schema import RegisterRequest, LoginRequest


@pytest.fixture
def auth_service():
    """Fixture que proporciona una instancia del AuthService"""
    return AuthService()


@pytest.fixture
def mock_db():
    """Fixture que proporciona un mock de la sesión de base de datos"""
    db = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.refresh = Mock()
    db.add = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def sample_user():
    """Fixture que proporciona un usuario de prueba"""
    user = User(
        email="test@example.com",
        username="Test User",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True
    )
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    return user


# Test básico para hash de contraseña
def test_hash_password(auth_service):
    """Test que verifica que se puede hashear una contraseña"""
    password = "mySecurePassword123"
    hashed = auth_service.hash_password(password)

    assert hashed is not None
    assert hashed != password


# Tests esenciales para registro de usuario
def test_register_user_success(auth_service, mock_db):
    """Test que verifica el registro exitoso de un usuario"""
    register_data = RegisterRequest(
        email="newuser@example.com",
        username="New User",
        password="securePass123"
    )

    def mock_add(user):
        user.id = "new-user-id"

    mock_db.add = mock_add

    result = auth_service.register_user(mock_db, register_data)

    assert result.email == register_data.email
    assert result.username == register_data.username
    assert result.is_active is True


# Tests esenciales para login
def test_authenticate_user_success(auth_service, mock_db, sample_user):
    """Test que verifica la autenticación exitosa de un usuario"""
    password = "correctPassword123"
    sample_user.hashed_password = auth_service.hash_password(password)

    login_data = LoginRequest(
        email="test@example.com",
        password=password
    )

    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = sample_user
    mock_db.query.return_value = mock_query

    result = auth_service.authenticate_user(mock_db, login_data)

    assert result.access_token is not None
    assert result.token_type == "bearer"
