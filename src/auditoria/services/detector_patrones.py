from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from db.models import AuditLog

logger = logging.getLogger(__name__)


class DetectorPatrones:
    """
    Detecta patrones sospechosos en operaciones de inventario.
    
    Patrones detectados:
    1. AJUSTE_MASIVO: Múltiples ajustes en corto tiempo por el mismo usuario
    2. ELIMINACION_SOSPECHOSA: Eliminación de grandes cantidades de stock
    3. ACTIVIDAD_NOCTURNA: Operaciones fuera del horario laboral (22:00 - 06:00)
    4. CAMBIO_ESTADO_RAPIDO: Cambios de estado frecuentes del mismo lote
    5. DISMINUCION_SIN_JUSTIFICACION: Stock que disminuye significativamente
    6. MULTIPLES_PRODUCTOS_MISMO_USUARIO: Muchos productos modificados por un usuario en poco tiempo
    """
    
    # Configuración de umbrales
    UMBRAL_AJUSTES_MASIVOS = 5  # 5 ajustes en 30 minutos
    VENTANA_AJUSTES_MASIVOS = 30  # minutos
    
    UMBRAL_CANTIDAD_ELIMINACION = 100  # unidades
    
    UMBRAL_CAMBIOS_ESTADO = 3  # 3 cambios en 1 hora
    VENTANA_CAMBIOS_ESTADO = 60  # minutos
    
    UMBRAL_PRODUCTOS_USUARIO = 10  # 10 productos diferentes en 1 hora
    VENTANA_PRODUCTOS_USUARIO = 60  # minutos
    
    def __init__(self, db: Session):
        self.db = db
    
    async def analizar_evento(self, evento: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analiza un evento de inventario y retorna alertas si detecta patrones sospechosos.
        
        Args:
            evento: Diccionario con los datos del evento
            
        Returns:
            Lista de alertas detectadas
        """
        alertas = []
        
        try:
            # 1. Detectar ajustes masivos
            if alerta := await self._detectar_ajustes_masivos(evento):
                alertas.append(alerta)
            
            # 2. Detectar eliminación sospechosa
            if alerta := await self._detectar_eliminacion_sospechosa(evento):
                alertas.append(alerta)
            
            # 3. Detectar actividad nocturna
            if alerta := self._detectar_actividad_nocturna(evento):
                alertas.append(alerta)
            
            # 4. Detectar cambios de estado rápidos
            if alerta := await self._detectar_cambios_estado_rapidos(evento):
                alertas.append(alerta)
            
            # 5. Detectar disminución sin justificación
            if alerta := await self._detectar_disminucion_sospechosa(evento):
                alertas.append(alerta)
            
            # 6. Detectar múltiples productos modificados por mismo usuario
            if alerta := await self._detectar_multiples_productos(evento):
                alertas.append(alerta)
                
        except Exception as e:
            logger.error(f"Error analizando evento: {e}", exc_info=True)
        
        return alertas
    
    async def _detectar_ajustes_masivos(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta si hay múltiples ajustes en corto tiempo por el mismo usuario"""
        operation = evento.get("operation", "")
        if operation not in ["AJUSTAR", "MODIFICAR", "ACTUALIZAR", "CREAR"]:
            return None
        
        usuario_id = evento.get("usuario_id")
        if not usuario_id:
            return None
        
        # Buscar operaciones del mismo usuario en los últimos N minutos
        hace_n_min = datetime.utcnow() - timedelta(minutes=self.VENTANA_AJUSTES_MASIVOS)
        
        count = self.db.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.usuario_id == usuario_id,
                AuditLog.operation.in_(["AJUSTAR", "MODIFICAR", "ACTUALIZAR", "CREAR"]),
                AuditLog.timestamp >= hace_n_min
            )
        ).scalar()
        
        if count >= self.UMBRAL_AJUSTES_MASIVOS:
            return {
                "tipo": "AJUSTE_MASIVO",
                "severidad": "ALTA",
                "mensaje": f"Usuario ha realizado {count} ajustes en los últimos {self.VENTANA_AJUSTES_MASIVOS} minutos",
                "descripcion": f"El usuario {usuario_id} ha realizado múltiples modificaciones en el inventario en un corto período de tiempo. Esto podría indicar un intento de manipulación del sistema.",
                "evento": evento,
                "metadatos": {
                    "cantidad_operaciones": count,
                    "ventana_minutos": self.VENTANA_AJUSTES_MASIVOS
                }
            }
        
        return None
    
    async def _detectar_eliminacion_sospechosa(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta eliminación de grandes cantidades"""
        operation = evento.get("operation", "")
        if operation not in ["ELIMINAR", "DELETE"]:
            return None
        
        datos = evento.get("datos", {})
        cantidad = datos.get("cantidad", 0)
        
        # Si se eliminan más de UMBRAL unidades
        if cantidad > self.UMBRAL_CANTIDAD_ELIMINACION:
            return {
                "tipo": "ELIMINACION_SOSPECHOSA",
                "severidad": "CRITICA",
                "mensaje": f"Eliminación de {cantidad} unidades detectada",
                "descripcion": f"Se ha eliminado una cantidad significativa de stock ({cantidad} unidades). Esta operación requiere revisión inmediata para verificar su legitimidad.",
                "evento": evento,
                "metadatos": {
                    "cantidad_eliminada": cantidad,
                    "umbral": self.UMBRAL_CANTIDAD_ELIMINACION
                }
            }
        
        return None
    
    def _detectar_actividad_nocturna(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta operaciones fuera del horario laboral"""
        timestamp_str = evento.get("timestamp")
        if not timestamp_str:
            return None
        
        try:
            # Parsear el timestamp
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            timestamp = datetime.fromisoformat(timestamp_str)
            hora = timestamp.hour
            
            # Horario sospechoso: 22:00 - 06:00
            if hora >= 22 or hora < 6:
                return {
                    "tipo": "ACTIVIDAD_NOCTURNA",
                    "severidad": "MEDIA",
                    "mensaje": f"Operación realizada a las {hora:02d}:00 hrs (horario no laboral)",
                    "descripcion": f"Se detectó una operación de inventario fuera del horario laboral normal. Operación: {evento.get('operation')} a las {timestamp.strftime('%H:%M:%S')}.",
                    "evento": evento,
                    "metadatos": {
                        "hora": hora,
                        "timestamp": timestamp.isoformat()
                    }
                }
        except Exception as e:
            logger.error(f"Error parseando timestamp: {e}")
        
        return None
    
    async def _detectar_cambios_estado_rapidos(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta cambios de estado frecuentes del mismo lote"""
        operation = evento.get("operation", "")
        if operation not in ["MODIFICAR", "ACTUALIZAR"]:
            return None
        
        inventario_id = evento.get("inventario_id")
        if not inventario_id:
            return None
        
        cambios = evento.get("cambios", {})
        # Verificar si hay cambios de estado (formato: {"estado": {"anterior": ..., "nuevo": ...}})
        if not cambios or "estado" not in cambios:
            return None
        
        # Buscar cambios de estado en la última hora
        hace_1_hora = datetime.utcnow() - timedelta(minutes=self.VENTANA_CAMBIOS_ESTADO)
        
        count = self.db.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.inventario_id == inventario_id,
                AuditLog.operation.in_(["MODIFICAR", "ACTUALIZAR"]),
                AuditLog.timestamp >= hace_1_hora
            )
        ).scalar()
        
        if count >= self.UMBRAL_CAMBIOS_ESTADO:
            return {
                "tipo": "CAMBIO_ESTADO_RAPIDO",
                "severidad": "ALTA",
                "mensaje": f"Lote modificado {count} veces en la última hora",
                "descripcion": f"El lote de inventario {inventario_id} ha sido modificado {count} veces en {self.VENTANA_CAMBIOS_ESTADO} minutos. Cambios frecuentes pueden indicar intentos de manipulación.",
                "evento": evento,
                "metadatos": {
                    "cantidad_cambios": count,
                    "ventana_minutos": self.VENTANA_CAMBIOS_ESTADO
                }
            }
        
        return None
    
    async def _detectar_disminucion_sospechosa(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta disminución significativa de stock"""
        operation = evento.get("operation", "")
        if operation not in ["DISMINUIR", "AJUSTAR"]:
            return None
        
        datos = evento.get("datos", {})
        cambios = evento.get("cambios", {})
        
        cantidad_anterior = cambios.get("cantidad_anterior", 0)
        cantidad_nueva = cambios.get("cantidad_nueva", 0)
        
        if cantidad_anterior > 0:
            diferencia = cantidad_anterior - cantidad_nueva
            porcentaje = (diferencia / cantidad_anterior) * 100
            
            # Si disminuye más del 50% o más de 50 unidades
            if porcentaje > 50 and diferencia > 50:
                return {
                    "tipo": "DISMINUCION_SOSPECHOSA",
                    "severidad": "ALTA",
                    "mensaje": f"Stock disminuyó {diferencia} unidades ({porcentaje:.1f}%)",
                    "descripcion": f"Se detectó una disminución significativa de stock: de {cantidad_anterior} a {cantidad_nueva} unidades. Esta reducción del {porcentaje:.1f}% requiere verificación.",
                    "evento": evento,
                    "metadatos": {
                        "cantidad_anterior": cantidad_anterior,
                        "cantidad_nueva": cantidad_nueva,
                        "diferencia": diferencia,
                        "porcentaje": porcentaje
                    }
                }
        
        return None
    
    async def _detectar_multiples_productos(self, evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta múltiples productos modificados por el mismo usuario en poco tiempo"""
        usuario_id = evento.get("usuario_id")
        if not usuario_id:
            return None
        
        # Buscar cuántos productos diferentes ha modificado en la última hora
        hace_1_hora = datetime.utcnow() - timedelta(minutes=self.VENTANA_PRODUCTOS_USUARIO)
        
        productos_distintos = self.db.query(func.count(func.distinct(AuditLog.producto_id))).filter(
            and_(
                AuditLog.usuario_id == usuario_id,
                AuditLog.timestamp >= hace_1_hora,
                AuditLog.producto_id.isnot(None)
            )
        ).scalar()
        
        if productos_distintos >= self.UMBRAL_PRODUCTOS_USUARIO:
            return {
                "tipo": "MULTIPLES_PRODUCTOS_MODIFICADOS",
                "severidad": "MEDIA",
                "mensaje": f"Usuario modificó {productos_distintos} productos diferentes en la última hora",
                "descripcion": f"El usuario {usuario_id} ha realizado operaciones en {productos_distintos} productos distintos en {self.VENTANA_PRODUCTOS_USUARIO} minutos. Actividad inusualmente alta.",
                "evento": evento,
                "metadatos": {
                    "productos_distintos": productos_distintos,
                    "ventana_minutos": self.VENTANA_PRODUCTOS_USUARIO
                }
            }
        
        return None







