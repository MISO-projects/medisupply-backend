from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.database import Base


class Conductor(Base):
    __tablename__ = "conductores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    documento = Column(String(50), nullable=False, unique=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    licencia_conducir = Column(String(50), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    rutas = relationship("Ruta", back_populates="conductor")

    def __init__(self, nombre: str, apellido: str, documento: str, licencia_conducir: str,
                 telefono: str = None, email: str = None, activo: bool = True):
        now = datetime.now(timezone.utc)
        self.nombre = nombre
        self.apellido = apellido
        self.documento = documento
        self.telefono = telefono
        self.email = email
        self.licencia_conducir = licencia_conducir
        self.activo = activo
        self.fecha_creacion = now
        self.fecha_actualizacion = now

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "nombre_completo": f"{self.nombre} {self.apellido}",
            "documento": self.documento,
            "telefono": self.telefono,
            "email": self.email,
            "licencia_conducir": self.licencia_conducir,
            "activo": self.activo,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    placa = Column(String(20), nullable=False, unique=True)
    marca = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    año = Column(Integer, nullable=True)
    tipo = Column(String(50), nullable=False)  # Camión, Camioneta, Furgón, etc.
    capacidad_kg = Column(Integer, nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    rutas = relationship("Ruta", back_populates="vehiculo")

    def __init__(self, placa: str, marca: str, modelo: str, tipo: str,
                 año: int = None, capacidad_kg: int = None, activo: bool = True):
        now = datetime.now(timezone.utc)
        self.placa = placa
        self.marca = marca
        self.modelo = modelo
        self.año = año
        self.tipo = tipo
        self.capacidad_kg = capacidad_kg
        self.activo = activo
        self.fecha_creacion = now
        self.fecha_actualizacion = now

    def to_dict(self):
        return {
            "id": self.id,
            "placa": self.placa,
            "marca": self.marca,
            "modelo": self.modelo,
            "año": self.año,
            "tipo": self.tipo,
            "capacidad_kg": self.capacidad_kg,
            "activo": self.activo,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }


class Ruta(Base):
    __tablename__ = "rutas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(String(10), nullable=False)  
    bodega_origen = Column(String(255), nullable=False)
    estado = Column(String(50), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=False)
    condiciones_almacenamiento = Column(String(100), nullable=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    paradas = relationship("Parada", back_populates="ruta", cascade="all, delete-orphan")
    conductor = relationship("Conductor", back_populates="rutas")
    vehiculo = relationship("Vehiculo", back_populates="rutas")

    def __init__(self, fecha: str, bodega_origen: str, estado: str, vehiculo_id: int, 
                 conductor_id: int, condiciones_almacenamiento: str = None):
        now = datetime.now(timezone.utc)
        self.fecha = fecha
        self.bodega_origen = bodega_origen
        self.estado = estado
        self.vehiculo_id = vehiculo_id
        self.conductor_id = conductor_id
        self.condiciones_almacenamiento = condiciones_almacenamiento
        self.fecha_creacion = now
        self.fecha_actualizacion = now

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha,
            "bodega_origen": self.bodega_origen,
            "estado": self.estado,
            "vehiculo_id": self.vehiculo_id,
            "conductor_id": self.conductor_id,
            "vehiculo_placa": self.vehiculo.placa if self.vehiculo else None,
            "vehiculo_info": f"{self.vehiculo.marca} {self.vehiculo.modelo}" if self.vehiculo else None,
            "conductor_nombre": f"{self.conductor.nombre} {self.conductor.apellido}" if self.conductor else None,
            "condiciones_almacenamiento": self.condiciones_almacenamiento,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "paradas": [parada.to_dict() for parada in self.paradas] if self.paradas else []
        }


class Parada(Base):
    __tablename__ = "paradas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruta_id = Column(Integer, ForeignKey("rutas.id"), nullable=False)
    cliente_id = Column(Integer, nullable=False)
    direccion = Column(String(500), nullable=False)
    contacto = Column(String(255), nullable=False)
    latitud = Column(Numeric(10, 8), nullable=True)  
    longitud = Column(Numeric(11, 8), nullable=True)
    orden = Column(Integer, nullable=True)  
    estado = Column(String(50), default="Pendiente") 
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    ruta = relationship("Ruta", back_populates="paradas")

    def __init__(self, ruta_id: int, cliente_id: int, direccion: str, contacto: str,
                 latitud: float = None, longitud: float = None, orden: int = None):
        now = datetime.now(timezone.utc)
        self.ruta_id = ruta_id
        self.cliente_id = cliente_id
        self.direccion = direccion
        self.contacto = contacto
        self.latitud = latitud
        self.longitud = longitud
        self.orden = orden
        self.estado = "Pendiente"
        self.fecha_creacion = now
        self.fecha_actualizacion = now

    def to_dict(self):
        return {
            "id": self.id,
            "ruta_id": self.ruta_id,
            "cliente_id": self.cliente_id,
            "direccion": self.direccion,
            "contacto": self.contacto,
            "latitud": float(self.latitud) if self.latitud else None,
            "longitud": float(self.longitud) if self.longitud else None,
            "orden": self.orden,
            "estado": self.estado,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

