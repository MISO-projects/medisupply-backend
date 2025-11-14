from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timedelta
import logging

from db.database import get_db
from db.models import AuditLog, Alerta, EmailNotificacion
from schemas.schemas import (
    EventoInventarioSchema,
    RegistrarEmailSchema,
    ActualizarEmailSchema,
    RevisarAlertaSchema
)
from services.detector_patrones import DetectorPatrones
from services.servicio_alertas import ServicioAlertas

logger = logging.getLogger(__name__)


class AuditoriaService:
    """Servicio principal de auditoría"""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.detector_patrones = DetectorPatrones(db)
        self.servicio_alertas = ServicioAlertas(db)
    
    async def procesar_evento_inventario(self, evento: EventoInventarioSchema) -> Dict[str, Any]:
        """
        Procesa un evento de inventario:
        1. Lo registra en audit_log
        2. Analiza patrones sospechosos
        3. Genera y envía alertas si es necesario
        
        Returns:
            Resumen del procesamiento
        """
        try:
            # 1. Registrar en audit_log
            audit_log = await self._registrar_audit_log(evento)
            
            # 2. Analizar patrones
            alertas_detectadas = await self.detector_patrones.analizar_evento(evento.dict())
            
            # 3. Si hay alertas, procesarlas y notificar
            alertas_creadas = []
            if alertas_detectadas:
                alertas_creadas = await self.servicio_alertas.procesar_y_notificar_alertas(
                    alertas_detectadas,
                    str(audit_log.id)
                )
            
            logger.info(
                f"Evento procesado: {evento.operation} - "
                f"Alertas generadas: {len(alertas_creadas)}"
            )
            
            return {
                "status": "processed",
                "audit_log_id": str(audit_log.id),
                "alertas_generadas": len(alertas_creadas),
                "alertas": [
                    {
                        "id": str(a.id),
                        "tipo": a.tipo,
                        "severidad": a.severidad,
                        "mensaje": a.mensaje
                    }
                    for a in alertas_creadas
                ]
            }
            
        except Exception as e:
            logger.error(f"Error procesando evento de inventario: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Error procesando evento: {str(e)}"
            )
    
    async def _registrar_audit_log(self, evento: EventoInventarioSchema) -> AuditLog:
        """Registra el evento en la tabla audit_log"""
        try:
            # Parsear timestamp
            timestamp = datetime.fromisoformat(evento.timestamp.replace('Z', '+00:00'))
            
            audit_log = AuditLog(
                event_type=evento.event_type,
                operation=evento.operation,
                inventario_id=evento.inventario_id,
                producto_id=evento.producto_id,
                usuario_id=evento.usuario_id,
                ip_origen=evento.ip_origen,
                datos_operacion=evento.datos,
                cambios=evento.cambios,
                timestamp=timestamp
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            return audit_log
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando audit_log: {e}")
            raise
    
    # --- Gestión de Emails ---
    
    def registrar_email(self, email_data: RegistrarEmailSchema) -> EmailNotificacion:
        """Registra un nuevo email para recibir notificaciones"""
        try:
            # Verificar si ya existe
            existe = self.db.query(EmailNotificacion).filter(
                EmailNotificacion.email == email_data.email
            ).first()
            
            if existe:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=f"El email {email_data.email} ya está registrado"
                )
            
            nuevo_email = EmailNotificacion(
                email=email_data.email,
                nombre=email_data.nombre,
                cargo=email_data.cargo,
                severidades_minimas=email_data.severidades_minimas,
                activo=True
            )
            
            self.db.add(nuevo_email)
            self.db.commit()
            self.db.refresh(nuevo_email)
            
            logger.info(f"Email registrado para notificaciones: {nuevo_email.email}")
            return nuevo_email
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando email: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al registrar el email"
            )
    
    def listar_emails(self, activos_solo: bool = False) -> List[EmailNotificacion]:
        """Lista todos los emails registrados"""
        try:
            query = self.db.query(EmailNotificacion)
            
            if activos_solo:
                query = query.filter(EmailNotificacion.activo == True)
            
            return query.order_by(EmailNotificacion.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error listando emails: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al listar los emails"
            )
    
    def actualizar_email(self, email_id: str, update_data: ActualizarEmailSchema) -> EmailNotificacion:
        """Actualiza la configuración de un email"""
        try:
            email_notif = self.db.query(EmailNotificacion).filter(
                EmailNotificacion.id == email_id
            ).first()
            
            if not email_notif:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Email no encontrado"
                )
            
            # Actualizar campos
            if update_data.nombre is not None:
                email_notif.nombre = update_data.nombre
            if update_data.cargo is not None:
                email_notif.cargo = update_data.cargo
            if update_data.activo is not None:
                email_notif.activo = update_data.activo
            if update_data.severidades_minimas is not None:
                email_notif.severidades_minimas = update_data.severidades_minimas
            
            self.db.commit()
            self.db.refresh(email_notif)
            
            logger.info(f"Email actualizado: {email_notif.email}")
            return email_notif
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando email: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al actualizar el email"
            )
    
    def eliminar_email(self, email_id: str) -> Dict[str, str]:
        """Elimina (desactiva) un email"""
        try:
            email_notif = self.db.query(EmailNotificacion).filter(
                EmailNotificacion.id == email_id
            ).first()
            
            if not email_notif:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Email no encontrado"
                )
            
            # Desactivar en lugar de eliminar
            email_notif.activo = False
            self.db.commit()
            
            logger.info(f"Email desactivado: {email_notif.email}")
            return {"message": f"Email {email_notif.email} desactivado correctamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando email: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al eliminar el email"
            )
    
    # --- Gestión de Alertas ---
    
    def listar_alertas(
        self,
        skip: int = 0,
        limit: int = 20,
        severidad: Optional[str] = None,
        estado: Optional[str] = None,
        tipo: Optional[str] = None
    ) -> tuple[List[Alerta], int]:
        """Lista alertas con filtros y paginación"""
        try:
            query = self.db.query(Alerta)
            
            # Aplicar filtros
            if severidad:
                query = query.filter(Alerta.severidad == severidad)
            if estado:
                query = query.filter(Alerta.estado == estado)
            if tipo:
                query = query.filter(Alerta.tipo == tipo)
            
            total = query.count()
            
            alertas = query.order_by(desc(Alerta.created_at)) \
                          .offset(skip) \
                          .limit(limit) \
                          .all()
            
            return alertas, total
            
        except Exception as e:
            logger.error(f"Error listando alertas: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al listar las alertas"
            )
    
    def obtener_alerta(self, alerta_id: str) -> Alerta:
        """Obtiene una alerta por ID"""
        try:
            alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
            
            if not alerta:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Alerta no encontrada"
                )
            
            return alerta
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo alerta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al obtener la alerta"
            )
    
    def revisar_alerta(self, alerta_id: str, revision_data: RevisarAlertaSchema) -> Alerta:
        """Marca una alerta como revisada/resuelta"""
        try:
            alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
            
            if not alerta:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Alerta no encontrada"
                )
            
            # Actualizar
            alerta.estado = revision_data.estado
            if revision_data.revisado_por:
                alerta.revisado_por = revision_data.revisado_por
            if revision_data.notas_revision:
                alerta.notas_revision = revision_data.notas_revision
            
            self.db.commit()
            self.db.refresh(alerta)
            
            logger.info(f"Alerta {alerta_id} actualizada a estado: {revision_data.estado}")
            return alerta
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revisando alerta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al revisar la alerta"
            )
    
    def obtener_estadisticas_alertas(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de alertas"""
        try:
            total_alertas = self.db.query(func.count(Alerta.id)).scalar()
            
            # Por severidad
            por_severidad = {}
            severidades = self.db.query(
                Alerta.severidad,
                func.count(Alerta.id)
            ).group_by(Alerta.severidad).all()
            
            for sev, count in severidades:
                por_severidad[sev] = count
            
            # Por estado
            por_estado = {}
            estados = self.db.query(
                Alerta.estado,
                func.count(Alerta.id)
            ).group_by(Alerta.estado).all()
            
            for est, count in estados:
                por_estado[est] = count
            
            # Por tipo
            por_tipo = {}
            tipos = self.db.query(
                Alerta.tipo,
                func.count(Alerta.id)
            ).group_by(Alerta.tipo).all()
            
            for tipo, count in tipos:
                por_tipo[tipo] = count
            
            # Últimas 24h
            hace_24h = datetime.utcnow() - timedelta(hours=24)
            alertas_24h = self.db.query(func.count(Alerta.id)).filter(
                Alerta.created_at >= hace_24h
            ).scalar()
            
            # Pendientes
            alertas_pendientes = self.db.query(func.count(Alerta.id)).filter(
                Alerta.estado == "PENDIENTE"
            ).scalar()
            
            return {
                "total_alertas": total_alertas,
                "por_severidad": por_severidad,
                "por_estado": por_estado,
                "por_tipo": por_tipo,
                "alertas_ultimas_24h": alertas_24h,
                "alertas_pendientes": alertas_pendientes
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error al obtener estadísticas"
            )


def get_auditoria_service(db: Session = Depends(get_db)) -> AuditoriaService:
    """Función de dependencia para obtener instancia del servicio"""
    return AuditoriaService(db)






