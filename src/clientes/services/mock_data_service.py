"""
Servicio para generar datos mock del servicio de clientes.
"""
from sqlalchemy.orm import Session
from models.cliente_institucional_model import ClienteInstitucional
from typing import Dict, List
import uuid


class MockDataService:

    def __init__(self, db: Session):
        self.db = db
    
    def get_mock_vendedor_ids(self) -> List[str]:
        return [
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "c3d4e5f6-a7b8-9012-cdef-123456789012",
        ]
    
    def get_mock_clientes_data(self) -> List[Dict]:
        vendedor_ids = self.get_mock_vendedor_ids()
        
        return [
            {
                "nombre": "Hospital General San José",
                "nit": "901234567-8",
                "id_vendedor": vendedor_ids[0],
                "logo_url": "https://storage.googleapis.com/logos/hospital-san-jose.png"
            },
            {
                "nombre": "Clínica Santa María",
                "nit": "901987654-3",
                "id_vendedor": vendedor_ids[0],
                "logo_url": "https://storage.googleapis.com/logos/clinica-santa-maria.png"
            },
            {
                "nombre": "Centro Médico del Norte",
                "nit": "900123456-7",
                "id_vendedor": vendedor_ids[0],
                "logo_url": "https://storage.googleapis.com/logos/centro-medico-norte.png"
            },
            {
                "nombre": "Hospital Universitario Nacional",
                "nit": "899999999-1",
                "id_vendedor": vendedor_ids[1],
                "logo_url": "https://storage.googleapis.com/logos/hospital-universitario.png"
            },
            {
                "nombre": "Clínica del Valle",
                "nit": "900555555-2",
                "id_vendedor": vendedor_ids[1],
                "logo_url": "https://storage.googleapis.com/logos/clinica-valle.png"
            },
            {
                "nombre": "Hospital Infantil Los Ángeles",
                "nit": "900777777-4",
                "id_vendedor": vendedor_ids[2],
                "logo_url": "https://storage.googleapis.com/logos/hospital-infantil.png"
            },
            {
                "nombre": "Centro de Salud Comunitario",
                "nit": "900888888-5",
                "id_vendedor": vendedor_ids[2],
                "logo_url": None
            }
        ]
    
    def create_mock_data(self, clear_existing: bool = False) -> Dict:

        try:
            clientes_eliminados = 0
            
            if clear_existing:
                clientes_eliminados = self.db.query(ClienteInstitucional).count()
                self.db.query(ClienteInstitucional).delete()
                self.db.commit()
            
            clientes_data = self.get_mock_clientes_data()
            
            clientes_creados = 0
            clientes_saltados = 0
            clientes_info = []
            
            for cliente_data in clientes_data:
                existing = self.db.query(ClienteInstitucional).filter_by(
                    nit=cliente_data["nit"]
                ).first()
                
                if not existing:
                    cliente = ClienteInstitucional(**cliente_data)
                    self.db.add(cliente)
                    clientes_creados += 1
                    clientes_info.append({
                        "id": str(cliente.id),
                        "nombre": cliente.nombre,
                        "nit": cliente.nit,
                        "id_vendedor": str(cliente.id_vendedor),
                        "estado": "creado"
                    })
                else:
                    clientes_saltados += 1
                    clientes_info.append({
                        "id": str(existing.id),
                        "nombre": existing.nombre,
                        "nit": existing.nit,
                        "id_vendedor": str(existing.id_vendedor),
                        "estado": "ya_existia"
                    })
            
            self.db.commit()
            
            total_clientes = self.db.query(ClienteInstitucional).count()
            
            return {
                "success": True,
                "message": "Datos mock creados exitosamente",
                "estadisticas": {
                    "clientes_eliminados": clientes_eliminados,
                    "clientes_creados": clientes_creados,
                    "clientes_saltados": clientes_saltados,
                    "total_en_bd": total_clientes
                },
                "vendedores_mock": self.get_mock_vendedor_ids(),
                "clientes": clientes_info
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error al crear datos mock: {str(e)}")
    
    def clear_all_data(self) -> Dict:
        try:
            count = self.db.query(ClienteInstitucional).count()
            self.db.query(ClienteInstitucional).delete()
            self.db.commit()
            
            return {
                "success": True,
                "message": "Todos los datos fueron eliminados",
                "clientes_eliminados": count
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error al eliminar datos: {str(e)}")
    
    def get_stats(self) -> Dict:
        try:
            total_clientes = self.db.query(ClienteInstitucional).count()
            
            vendedores_mock = self.get_mock_vendedor_ids()
            clientes_por_vendedor = {}
            
            for vendedor_id in vendedores_mock:
                count = self.db.query(ClienteInstitucional).filter_by(
                    id_vendedor=uuid.UUID(vendedor_id)
                ).count()
                clientes_por_vendedor[vendedor_id] = count
            
            return {
                "total_clientes": total_clientes,
                "clientes_por_vendedor": clientes_por_vendedor,
                "vendedores_mock": vendedores_mock
            }
            
        except Exception as e:
            raise Exception(f"Error al obtener estadísticas: {str(e)}")
    
    def generate_clientes_for_vendedor(self, vendedor_id: str, cantidad: int = 5) -> Dict:

        import random
        
        try:
            try:
                uuid_vendedor = uuid.UUID(vendedor_id)
            except ValueError:
                raise Exception(f"ID de vendedor inválido: {vendedor_id}")
            
            if cantidad < 1 or cantidad > 50:
                raise Exception("La cantidad debe estar entre 1 y 50")
            
            tipos_instituciones = [
                "Hospital", "Clínica", "Centro Médico", "Policlínica", 
                "Centro de Salud", "Hospital Universitario", "Clínica Especializada",
                "Centro Hospitalario", "Instituto Médico"
            ]
            
            nombres = [
                "San José", "Santa María", "del Norte", "del Sur", "Central",
                "Los Ángeles", "La Esperanza", "San Rafael", "Santa Cruz",
                "del Valle", "San Juan", "Metropolitano", "Regional",
                "Nacional", "General", "Comunitario", "Infantil",
                "de la Mujer", "de Especialidades", "Integral"
            ]
            
            clientes_generados = []
            clientes_creados = 0
            intentos_fallidos = 0
            max_intentos = cantidad * 3
            
            while clientes_creados < cantidad and intentos_fallidos < max_intentos:
                tipo = random.choice(tipos_instituciones)
                nombre_base = random.choice(nombres)
                nombre_completo = f"{tipo} {nombre_base}"
                
                nit_numero = random.randint(800000000, 999999999)
                nit_verificacion = random.randint(0, 9)
                nit = f"{nit_numero}-{nit_verificacion}"
                
                existing = self.db.query(ClienteInstitucional).filter_by(nit=nit).first()
                
                if not existing:
                    logo_url = None
                    if random.random() < 0.7:
                        logo_slug = nombre_completo.lower().replace(" ", "-")
                        logo_url = f"https://storage.googleapis.com/logos/{logo_slug}.png"
                    
                    cliente = ClienteInstitucional(
                        nombre=nombre_completo,
                        nit=nit,
                        id_vendedor=vendedor_id,
                        logo_url=logo_url
                    )
                    
                    self.db.add(cliente)
                    clientes_creados += 1
                    
                    clientes_generados.append({
                        "id": str(cliente.id),
                        "nombre": cliente.nombre,
                        "nit": cliente.nit,
                        "logoUrl": cliente.logo_url
                    })
                else:
                    intentos_fallidos += 1
            
            self.db.commit()
            
            total_vendedor = self.db.query(ClienteInstitucional).filter_by(
                id_vendedor=uuid_vendedor
            ).count()
            
            return {
                "success": True,
                "message": f"Se generaron {clientes_creados} clientes para el vendedor",
                "vendedor_id": vendedor_id,
                "clientes_generados": clientes_creados,
                "total_clientes_vendedor": total_vendedor,
                "clientes": clientes_generados
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error al generar clientes: {str(e)}")

