from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.producto import Producto
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class InitService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_productos_ejemplo(self) -> list[Producto]:
        return [
            Producto(
                nombre="Paracetamol 500mg",
                descripcion="Analgésico y antipirético. Caja con 100 tabletas",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/paracetamol.jpg",
                precio_unitario=15.50,
                stock_disponible=250,
                disponible=True,
                unidad_medida="CAJA",
                sku="MED-PAR-500-100"
            ),
            Producto(
                nombre="Ibuprofeno 400mg",
                descripcion="Antiinflamatorio no esteroideo. Caja con 50 tabletas",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/ibuprofeno.jpg",
                precio_unitario=22.00,
                stock_disponible=180,
                disponible=True,
                unidad_medida="CAJA",
                sku="MED-IBU-400-50"
            ),
            Producto(
                nombre="Amoxicilina 500mg",
                descripcion="Antibiótico de amplio espectro. Caja con 21 cápsulas",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/amoxicilina.jpg",
                precio_unitario=35.75,
                stock_disponible=95,
                disponible=True,
                unidad_medida="CAJA",
                sku="MED-AMO-500-21"
            ),
            Producto(
                nombre="Omeprazol 20mg",
                descripcion="Inhibidor de la bomba de protones. Caja con 28 cápsulas",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/omeprazol.jpg",
                precio_unitario=28.50,
                stock_disponible=140,
                disponible=True,
                unidad_medida="CAJA",
                sku="MED-OME-20-28"
            ),
            # Insumos médicos
            Producto(
                nombre="Guantes de látex talla M",
                descripcion="Guantes desechables de látex. Caja con 100 unidades",
                categoria="INSUMOS",
                imagen_url="https://example.com/images/guantes-latex.jpg",
                precio_unitario=45.00,
                stock_disponible=320,
                disponible=True,
                unidad_medida="CAJA",
                sku="INS-GLV-LAT-M-100"
            ),
            Producto(
                nombre="Jeringas 10ml con aguja",
                descripcion="Jeringas desechables estériles. Caja con 100 unidades",
                categoria="INSUMOS",
                imagen_url="https://example.com/images/jeringas.jpg",
                precio_unitario=55.00,
                stock_disponible=200,
                disponible=True,
                unidad_medida="CAJA",
                sku="INS-JER-10ML-100"
            ),
            Producto(
                nombre="Gasas estériles 10x10cm",
                descripcion="Gasas estériles de algodón. Caja con 100 sobres",
                categoria="INSUMOS",
                imagen_url="https://example.com/images/gasas.jpg",
                precio_unitario=38.00,
                stock_disponible=175,
                disponible=True,
                unidad_medida="CAJA",
                sku="INS-GAS-10X10-100"
            ),
            Producto(
                nombre="Alcohol en gel 500ml",
                descripcion="Alcohol en gel desinfectante 70%. Botella de 500ml",
                categoria="INSUMOS",
                imagen_url="https://example.com/images/alcohol-gel.jpg",
                precio_unitario=12.50,
                stock_disponible=450,
                disponible=True,
                unidad_medida="UNIDAD",
                sku="INS-ALC-GEL-500"
            ),
            Producto(
                nombre="Tensiómetro digital de brazo",
                descripcion="Tensiómetro digital automático con memoria para 2 usuarios",
                categoria="EQUIPOS",
                imagen_url="https://example.com/images/tensiometro.jpg",
                precio_unitario=185.00,
                stock_disponible=45,
                disponible=True,
                unidad_medida="UNIDAD",
                sku="EQU-TEN-DIG-BR"
            ),
            Producto(
                nombre="Termómetro digital infrarrojo",
                descripcion="Termómetro sin contacto con lectura en 1 segundo",
                categoria="EQUIPOS",
                imagen_url="https://example.com/images/termometro-infrarrojo.jpg",
                precio_unitario=95.00,
                stock_disponible=68,
                disponible=True,
                unidad_medida="UNIDAD",
                sku="EQU-TER-INF"
            ),
            Producto(
                nombre="Nebulizador ultrasónico",
                descripcion="Nebulizador ultrasónico portátil con compresor",
                categoria="EQUIPOS",
                imagen_url="https://example.com/images/nebulizador.jpg",
                precio_unitario=245.00,
                stock_disponible=28,
                disponible=True,
                unidad_medida="UNIDAD",
                sku="EQU-NEB-ULT"
            ),
            # Productos sin stock (para testing)
            Producto(
                nombre="Insulina Glargina 100UI",
                descripcion="Insulina de acción prolongada. Caja con 5 plumas precargadas",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/insulina.jpg",
                precio_unitario=285.00,
                stock_disponible=0,
                disponible=True,
                unidad_medida="CAJA",
                sku="MED-INS-GLA-100"
            ),
            Producto(
                nombre="Vacuna contra Influenza",
                descripcion="Vacuna trivalente contra influenza estacional",
                categoria="MEDICAMENTOS",
                imagen_url="https://example.com/images/vacuna-influenza.jpg",
                precio_unitario=125.00,
                stock_disponible=0,
                disponible=False,
                unidad_medida="DOSIS",
                sku="MED-VAC-INF-TRI"
            ),
        ]
    
    def inicializar_productos(self, force: bool = False) -> Dict[str, Any]:

        try:
            count_antes = self.db.query(Producto).count()
            
            if force:
                logger.info("Modo force activado. Eliminando productos existentes...")
                self.db.query(Producto).delete()
                self.db.commit()
                logger.info(f"Se eliminaron {count_antes} productos")
                count_antes = 0
            
            if count_antes > 0:
                logger.info(f"Ya existen {count_antes} productos. Use force=true para reinicializar.")
                return {
                    "status": "skipped",
                    "message": f"Ya existen {count_antes} productos en la base de datos. Use force=true para reinicializar.",
                    "productos_existentes": count_antes,
                    "productos_creados": 0
                }
            
            productos_ejemplo = self.get_productos_ejemplo()
            
            for producto in productos_ejemplo:
                self.db.add(producto)
            
            self.db.commit()
            
            total = self.db.query(Producto).count()
            disponibles = self.db.query(Producto).filter(Producto.disponible == True).count()
            con_stock = self.db.query(Producto).filter(
                and_(
                    Producto.disponible == True,
                    Producto.stock_disponible > 0
                )
            ).count()
            
            medicamentos = self.db.query(Producto).filter(Producto.categoria == "MEDICAMENTOS").count()
            insumos = self.db.query(Producto).filter(Producto.categoria == "INSUMOS").count()
            equipos = self.db.query(Producto).filter(Producto.categoria == "EQUIPOS").count()
            
            logger.info(f"✅ Se crearon {len(productos_ejemplo)} productos de ejemplo exitosamente")
            
            return {
                "status": "success",
                "message": f"Se crearon {len(productos_ejemplo)} productos de ejemplo exitosamente",
                "productos_creados": len(productos_ejemplo),
                "estadisticas": {
                    "total": total,
                    "disponibles": disponibles,
                    "con_stock": con_stock,
                    "por_categoria": {
                        "MEDICAMENTOS": medicamentos,
                        "INSUMOS": insumos,
                        "EQUIPOS": equipos
                    }
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al inicializar productos: {str(e)}")
            raise
    
    def limpiar_productos(self) -> Dict[str, Any]:

        try:
            count = self.db.query(Producto).count()
            
            if count == 0:
                return {
                    "status": "skipped",
                    "message": "No hay productos para eliminar",
                    "productos_eliminados": 0
                }
            
            self.db.query(Producto).delete()
            self.db.commit()
            
            logger.info(f"✅ Se eliminaron {count} productos exitosamente")
            
            return {
                "status": "success",
                "message": f"Se eliminaron {count} productos exitosamente",
                "productos_eliminados": count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al limpiar productos: {str(e)}")
            raise

