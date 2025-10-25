import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from models.ruta_model import Ruta, Parada
from services.ruta_service import RutaService
from schemas.ruta_schema import RutaCreateRequest, ParadaRequest
from fastapi import HTTPException


TEST_DATABASE_URL = "sqlite:///./test_logistica.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    from models.ruta_model import Conductor, Vehiculo
    
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # Crear datos de prueba con SQL directo para especificar el ID
        session.execute(
            Conductor.__table__.insert(),
            {
                "id": 4,
                "nombre": "Juan",
                "apellido": "Pérez",
                "documento": "1234567890",
                "telefono": "3001234567",
                "email": "juan.perez@test.com",
                "licencia_conducir": "C2-12345678",
                "activo": True
            }
        )
        
        session.execute(
            Vehiculo.__table__.insert(),
            {
                "id": 12,
                "placa": "ABC123",
                "marca": "Chevrolet",
                "modelo": "NQR",
                "año": 2022,
                "tipo": "Camión refrigerado",
                "capacidad_kg": 3500,
                "activo": True
            }
        )
        
        session.commit()
        
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def ruta_service(db_session):
    return RutaService(db=db_session)


@pytest.fixture
def ruta_data_valida():
    return RutaCreateRequest(
        fecha="2025-08-17",
        bodega_origen="Central Bogotá",
        estado="Pendiente",
        vehiculo_id=12,
        conductor_id=4,
        condiciones_almacenamiento="Refrigerado",
        paradas=[
            ParadaRequest(
                cliente_id=32,
                direccion="Calle 80 #45-20",
                contacto="Carlos Ríos",
                latitud=4.7110,
                longitud=-74.0721
            ),
            ParadaRequest(
                cliente_id=15,
                direccion="Av. 30 #22-10",
                contacto="María López",
                latitud=4.6097,
                longitud=-74.0817
            )
        ]
    )


class TestRutaService:

    def test_crear_ruta_exitosamente(self, ruta_service, ruta_data_valida):
        # Act
        resultado = ruta_service.crear_ruta(ruta_data_valida)
        
        # Assert
        assert resultado.id is not None
        assert resultado.id > 0
        assert resultado.mensaje == "Ruta creada exitosamente"
    
    def test_crear_ruta_persiste_datos(self, ruta_service, ruta_data_valida, db_session):
        # Act
        resultado = ruta_service.crear_ruta(ruta_data_valida)
        
        # Verificar en la base de datos
        ruta_db = db_session.query(Ruta).filter(Ruta.id == resultado.id).first()
        
        # Assert
        assert ruta_db is not None
        assert ruta_db.fecha == ruta_data_valida.fecha
        assert ruta_db.bodega_origen == ruta_data_valida.bodega_origen
        assert ruta_db.estado == ruta_data_valida.estado
        assert ruta_db.vehiculo_id == ruta_data_valida.vehiculo_id
        assert ruta_db.conductor_id == ruta_data_valida.conductor_id
        assert ruta_db.condiciones_almacenamiento == ruta_data_valida.condiciones_almacenamiento
    
    def test_crear_ruta_con_paradas(self, ruta_service, ruta_data_valida, db_session):
        # Act
        resultado = ruta_service.crear_ruta(ruta_data_valida)
        
        # Verificar paradas en la base de datos
        paradas_db = db_session.query(Parada).filter(Parada.ruta_id == resultado.id).all()
        
        # Assert
        assert len(paradas_db) == 2
        assert paradas_db[0].cliente_id == 32
        assert paradas_db[0].direccion == "Calle 80 #45-20"
        assert paradas_db[0].contacto == "Carlos Ríos"
        assert float(paradas_db[0].latitud) == 4.7110
        assert float(paradas_db[0].longitud) == -74.0721
        assert paradas_db[1].cliente_id == 15
    
    def test_obtener_ruta_existente(self, ruta_service, ruta_data_valida):
        # Arrange
        resultado_crear = ruta_service.crear_ruta(ruta_data_valida)
        
        # Act
        ruta = ruta_service.obtener_ruta(resultado_crear.id)
        
        # Assert
        assert ruta.id == resultado_crear.id
        assert ruta.fecha == ruta_data_valida.fecha
        assert ruta.bodega_origen == ruta_data_valida.bodega_origen
        assert len(ruta.paradas) == 2
    
    def test_obtener_ruta_inexistente(self, ruta_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            ruta_service.obtener_ruta(999)
        
        assert exc_info.value.status_code == 404
        assert "no encontrada" in str(exc_info.value.detail).lower()
    
    def test_listar_rutas(self, ruta_service, ruta_data_valida):
        ruta_service.crear_ruta(ruta_data_valida)
        
        ruta_data_2 = ruta_data_valida.model_copy()
        ruta_data_2.fecha = "2025-08-18"
        ruta_service.crear_ruta(ruta_data_2)
        
        # Act
        resultado = ruta_service.listar_rutas()
        
        # Assert
        assert resultado.total == 2
        assert len(resultado.rutas) == 2
        assert resultado.rutas[0].fecha == "2025-08-17"
        assert resultado.rutas[1].fecha == "2025-08-18"
    
    def test_listar_rutas_con_paginacion(self, ruta_service, ruta_data_valida):
        for i in range(3):
            ruta_data = ruta_data_valida.model_copy()
            ruta_data.fecha = f"2025-08-{17+i}"
            ruta_service.crear_ruta(ruta_data)
        
        # Act
        resultado = ruta_service.listar_rutas(page=1, page_size=2)
        
        # Assert
        assert resultado.total == 3
        assert len(resultado.rutas) == 2
        assert resultado.page == 1
        assert resultado.page_size == 2
        assert resultado.total_pages == 2
    
    def test_crear_ruta_con_orden_personalizado(self, ruta_service, db_session):
        # Arrange
        ruta_data = RutaCreateRequest(
            fecha="2025-08-17",
            bodega_origen="Central Bogotá",
            estado="Pendiente",
            vehiculo_id=12,
            conductor_id=4,
            paradas=[
                ParadaRequest(
                    cliente_id=32,
                    direccion="Calle 80 #45-20",
                    contacto="Carlos Ríos",
                    orden=2
                ),
                ParadaRequest(
                    cliente_id=15,
                    direccion="Av. 30 #22-10",
                    contacto="María López",
                    orden=1
                )
            ]
        )
        
        # Act
        resultado = ruta_service.crear_ruta(ruta_data)
        
        # Assert
        paradas_db = db_session.query(Parada).filter(
            Parada.ruta_id == resultado.id
        ).order_by(Parada.orden).all()
        
        assert paradas_db[0].orden == 1
        assert paradas_db[0].cliente_id == 15
        assert paradas_db[1].orden == 2
        assert paradas_db[1].cliente_id == 32
    
    def test_crear_ruta_sin_orden_asigna_secuencial(self, ruta_service, db_session):
        # Arrange
        ruta_data = RutaCreateRequest(
            fecha="2025-08-17",
            bodega_origen="Central Bogotá",
            estado="Pendiente",
            vehiculo_id=12,
            conductor_id=4,
            paradas=[
                ParadaRequest(
                    cliente_id=32,
                    direccion="Calle 80 #45-20",
                    contacto="Carlos Ríos"
                ),
                ParadaRequest(
                    cliente_id=15,
                    direccion="Av. 30 #22-10",
                    contacto="María López"
                )
            ]
        )
        
        # Act
        resultado = ruta_service.crear_ruta(ruta_data)
        
        # Assert
        paradas_db = db_session.query(Parada).filter(
            Parada.ruta_id == resultado.id
        ).order_by(Parada.id).all()
        
        assert paradas_db[0].orden == 1
        assert paradas_db[1].orden == 2

