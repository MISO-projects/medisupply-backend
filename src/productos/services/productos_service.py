from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from models.producto import Producto
from schemas.producto_schema import ProductoCreate, ProductoUpdate, ProductoConStock
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ProductosService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_productos_disponibles(
        self,
        solo_con_stock: bool = True,
        categoria: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ProductoConStock], int]:
        """
        Obtiene la lista de productos disponibles con stock
        
        Args:
            solo_con_stock: Si True, solo retorna productos con stock > 0
            categoria: Filtro opcional por categoría
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Tupla con (lista de productos, total de productos)
        """
        try:
            # Construir query base
            query = self.db.query(Producto)
            
            # Aplicar filtros
            filters = [Producto.disponible == True]
            
            if solo_con_stock:
                filters.append(Producto.stock_disponible > 0)
            
            if categoria:
                filters.append(Producto.categoria == categoria)
            
            query = query.filter(and_(*filters))
            
            # Obtener total
            total = query.count()
            
            # Aplicar paginación y ordenamiento
            productos = query.order_by(Producto.nombre).offset(skip).limit(limit).all()
            
            # Convertir a schema
            productos_response = [
                ProductoConStock.model_validate(producto) for producto in productos
            ]
            
            logger.info(f"Se encontraron {total} productos disponibles")
            return productos_response, total
            
        except Exception as e:
            logger.error(f"Error al obtener productos disponibles: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al obtener productos disponibles"
            )
    
    def get_producto_by_id(self, producto_id: str) -> Optional[Producto]:
        """Obtiene un producto por su ID"""
        try:
            producto = self.db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto con ID {producto_id} no encontrado"
                )
            return producto
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener producto {producto_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al obtener producto"
            )
    
    def crear_producto(self, producto_data: ProductoCreate) -> Producto:
        """Crea un nuevo producto"""
        try:
            # Verificar si ya existe un producto con el mismo SKU
            if producto_data.sku:
                existing = self.db.query(Producto).filter(Producto.sku == producto_data.sku).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ya existe un producto con el SKU {producto_data.sku}"
                    )
            
            nuevo_producto = Producto(**producto_data.model_dump())
            self.db.add(nuevo_producto)
            self.db.commit()
            self.db.refresh(nuevo_producto)
            
            logger.info(f"Producto creado: {nuevo_producto.id} - {nuevo_producto.nombre}")
            return nuevo_producto
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear producto: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al crear producto"
            )
    
    def actualizar_producto(self, producto_id: str, producto_data: ProductoUpdate) -> Producto:
        """Actualiza un producto existente"""
        try:
            producto = self.get_producto_by_id(producto_id)
            
            # Actualizar solo los campos proporcionados
            update_data = producto_data.model_dump(exclude_unset=True)
            
            # Verificar SKU único si se está actualizando
            if 'sku' in update_data and update_data['sku']:
                existing = self.db.query(Producto).filter(
                    Producto.sku == update_data['sku'],
                    Producto.id != producto_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ya existe otro producto con el SKU {update_data['sku']}"
                    )
            
            for field, value in update_data.items():
                setattr(producto, field, value)
            
            self.db.commit()
            self.db.refresh(producto)
            
            logger.info(f"Producto actualizado: {producto.id}")
            return producto
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar producto {producto_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al actualizar producto"
            )
    
    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto (soft delete marcándolo como no disponible)"""
        try:
            producto = self.get_producto_by_id(producto_id)
            producto.disponible = False
            self.db.commit()
            
            logger.info(f"Producto marcado como no disponible: {producto_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar producto {producto_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al eliminar producto"
            )
    
    def actualizar_stock(self, producto_id: str, cantidad: int) -> Producto:
        """Actualiza el stock de un producto"""
        try:
            producto = self.get_producto_by_id(producto_id)
            
            nuevo_stock = producto.stock_disponible + cantidad
            if nuevo_stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail="No hay suficiente stock disponible"
                )
            
            producto.stock_disponible = nuevo_stock
            self.db.commit()
            self.db.refresh(producto)
            
            logger.info(f"Stock actualizado para producto {producto_id}: {nuevo_stock}")
            return producto
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar stock del producto {producto_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al actualizar stock"
            )

