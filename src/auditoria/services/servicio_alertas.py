from typing import Dict, Any, List
import httpx
import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import Alerta, EmailNotificacion, AuditLog

logger = logging.getLogger(__name__)


class ServicioAlertas:
    """Gestiona el registro y envío de alertas de seguridad"""
    
    def __init__(self, db: Session):
        self.db = db
        # URL del servicio de email (puedes implementar uno o usar un servicio externo)
        self.email_api_url = os.getenv("EMAIL_SERVICE_URL")
        # Configuración SMTP alternativa
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = os.getenv("SMTP_PORT", "587")
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from = os.getenv("SMTP_FROM", "alertas@medisupply.com")
    
    async def procesar_y_notificar_alertas(
        self, 
        alertas: List[Dict[str, Any]], 
        audit_log_id: str = None
    ) -> List[Alerta]:
        """
        Procesa alertas: las guarda en BD y envía notificaciones.
        
        Args:
            alertas: Lista de diccionarios con datos de alertas
            audit_log_id: ID del registro de auditoría relacionado
            
        Returns:
            Lista de objetos Alerta creados
        """
        alertas_creadas = []
        
        for alerta_data in alertas:
            try:
                # Guardar alerta en base de datos
                alerta = await self._guardar_alerta(alerta_data, audit_log_id)
                alertas_creadas.append(alerta)
                
                # Enviar notificaciones
                await self._enviar_notificaciones(alerta, alerta_data)
                
            except Exception as e:
                logger.error(f"Error procesando alerta: {e}", exc_info=True)
        
        return alertas_creadas
    
    async def _guardar_alerta(
        self, 
        alerta_data: Dict[str, Any], 
        audit_log_id: str = None
    ) -> Alerta:
        """Guarda una alerta en la base de datos"""
        try:
            nueva_alerta = Alerta(
                tipo=alerta_data.get("tipo"),
                severidad=alerta_data.get("severidad"),
                mensaje=alerta_data.get("mensaje"),
                descripcion_detallada=alerta_data.get("descripcion"),
                evento_relacionado=alerta_data.get("evento"),
                audit_log_id=audit_log_id,
                estado="PENDIENTE",
                notificacion_enviada=False
            )
            
            self.db.add(nueva_alerta)
            self.db.commit()
            self.db.refresh(nueva_alerta)
            
            logger.info(f"Alerta guardada: {nueva_alerta.tipo} - {nueva_alerta.id}")
            return nueva_alerta
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error guardando alerta: {e}")
            raise
    
    async def _enviar_notificaciones(self, alerta: Alerta, alerta_data: Dict[str, Any]):
        """Envía notificaciones de la alerta por diferentes canales"""
        try:
            # Siempre registrar en logs
            await self._enviar_a_log(alerta, alerta_data)
            
            # Enviar emails solo para severidades configuradas
            if alerta.severidad in ["ALTA", "CRITICA"]:
                await self._enviar_emails(alerta, alerta_data)
                
                # Marcar como notificada
                alerta.notificacion_enviada = True
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones: {e}")
    
    async def _enviar_a_log(self, alerta: Alerta, alerta_data: Dict[str, Any]):
        """Registra la alerta en el log"""
        emoji_severidad = {
            "BAJA": "ℹ️",
            "MEDIA": "⚠️",
            "ALTA": "🔴",
            "CRITICA": "🚨"
        }
        
        logger.warning(
            f"{emoji_severidad.get(alerta.severidad, '⚠️')} ALERTA DE SEGURIDAD: "
            f"{alerta.tipo} - Severidad: {alerta.severidad} - {alerta.mensaje}"
        )
    
    async def _enviar_emails(self, alerta: Alerta, alerta_data: Dict[str, Any]):
        """Envía alertas por email a los destinatarios configurados"""
        try:
            # Obtener emails activos que deban recibir esta severidad
            destinatarios = self.db.query(EmailNotificacion).filter(
                and_(
                    EmailNotificacion.activo == True,
                    EmailNotificacion.severidades_minimas.contains([alerta.severidad])
                )
            ).all()
            
            if not destinatarios:
                logger.info("No hay destinatarios configurados para esta alerta")
                return
            
            emails = [d.email for d in destinatarios]
            
            # Preparar contenido del email
            asunto = f"🚨 Alerta de Inventario: {alerta.tipo} - {alerta.severidad}"
            cuerpo = self._formatear_email_html(alerta, alerta_data)
            
            # Intentar enviar usando el servicio de email si está configurado
            if self.email_api_url:
                await self._enviar_via_api(emails, asunto, cuerpo)
            elif self.smtp_host and self.smtp_user and self.smtp_password:
                await self._enviar_via_smtp(emails, asunto, cuerpo)
            else:
                logger.warning("No hay servicio de email configurado. Emails no enviados.")
                logger.info(f"Emails que recibirían la alerta: {', '.join(emails)}")
            
        except Exception as e:
            logger.error(f"Error enviando emails: {e}")
    
    async def _enviar_via_api(self, emails: List[str], asunto: str, cuerpo: str):
        """Envía email a través de un servicio API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for email in emails:
                    response = await client.post(
                        f"{self.email_api_url}/send",
                        json={
                            "to": email,
                            "subject": asunto,
                            "html_body": cuerpo
                        }
                    )
                    if response.status_code == 200:
                        logger.info(f"Email enviado a {email}")
                    else:
                        logger.error(f"Error enviando email a {email}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error en envío via API: {e}")
    
    async def _enviar_via_smtp(self, emails: List[str], asunto: str, cuerpo: str):
        """Envía email directamente vía SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Crear mensaje
            msg = MIMEMultipart("alternative")
            msg["Subject"] = asunto
            msg["From"] = self.smtp_from
            msg["To"] = ", ".join(emails)
            
            # Adjuntar el HTML
            html_part = MIMEText(cuerpo, "html")
            msg.attach(html_part)
            
            # Enviar
            with smtplib.SMTP(self.smtp_host, int(self.smtp_port)) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Emails enviados vía SMTP a {len(emails)} destinatarios")
            
        except Exception as e:
            logger.error(f"Error en envío via SMTP: {e}")
    
    def _formatear_email_html(self, alerta: Alerta, alerta_data: Dict[str, Any]) -> str:
        """Formatea el contenido HTML del email"""
        evento = alerta_data.get("evento", {})
        metadatos = alerta_data.get("metadatos", {})
        
        # Colores según severidad
        color_severidad = {
            "BAJA": "#17a2b8",
            "MEDIA": "#ffc107",
            "ALTA": "#fd7e14",
            "CRITICA": "#dc3545"
        }
        
        color = color_severidad.get(alerta.severidad, "#6c757d")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: {color};
                    color: white;
                    padding: 20px;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                }}
                .section {{
                    background-color: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid {color};
                }}
                .label {{
                    font-weight: bold;
                    color: #495057;
                }}
                .value {{
                    color: #212529;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 15px;
                    background-color: #e9ecef;
                    border-radius: 0 0 5px 5px;
                    font-size: 12px;
                    text-align: center;
                }}
                pre {{
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 3px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Alerta de Seguridad - Sistema de Inventario</h2>
            </div>
            
            <div class="content">
                <div class="section">
                    <p><span class="label">Tipo de Alerta:</span> <span class="value">{alerta.tipo}</span></p>
                    <p><span class="label">Severidad:</span> <span class="value" style="color: {color}; font-weight: bold;">{alerta.severidad}</span></p>
                    <p><span class="label">Mensaje:</span> <span class="value">{alerta.mensaje}</span></p>
                    <p><span class="label">Fecha/Hora:</span> <span class="value">{alerta.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span></p>
                </div>
                
                <div class="section">
                    <h3>Descripción Detallada</h3>
                    <p>{alerta.descripcion_detallada or 'Sin descripción adicional'}</p>
                </div>
                
                <div class="section">
                    <h3>Detalles del Evento</h3>
                    <p><span class="label">Operación:</span> <span class="value">{evento.get('operation', 'N/A')}</span></p>
                    <p><span class="label">Usuario ID:</span> <span class="value">{evento.get('usuario_id', 'Desconocido')}</span></p>
                    <p><span class="label">IP Origen:</span> <span class="value">{evento.get('ip_origen', 'Desconocida')}</span></p>
                    <p><span class="label">Inventario ID:</span> <span class="value">{evento.get('inventario_id', 'N/A')}</span></p>
                    <p><span class="label">Producto ID:</span> <span class="value">{evento.get('producto_id', 'N/A')}</span></p>
                </div>
                
                {self._formatear_metadatos_html(metadatos) if metadatos else ''}
            </div>
            
            <div class="footer">
                <p>Este es un mensaje automático del Sistema de Auditoría de MediSupply</p>
                <p>Por favor, revise esta alerta en el dashboard administrativo</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _formatear_metadatos_html(self, metadatos: Dict[str, Any]) -> str:
        """Formatea los metadatos en HTML"""
        if not metadatos:
            return ""
        
        items = ""
        for key, value in metadatos.items():
            items += f"<p><span class='label'>{key.replace('_', ' ').title()}:</span> <span class='value'>{value}</span></p>"
        
        return f"""
        <div class="section">
            <h3>Información Adicional</h3>
            {items}
        </div>
        """






