from typing import Dict, Any
from sqlalchemy.orm import Session
from ..db.order_projection_model import OrderProjection
from ..db.database import get_db
from fastapi import Depends
from http import HTTPStatus
from fastapi import HTTPException


class OrderProjectionHandler:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def handle_order_created_event(self, event_data: Dict[str, Any]):
        try:
            projection = OrderProjection(event_data)

            self.db.add(projection)
            self.db.commit()
            self.db.refresh(projection)

            print(f"Order projection created for order: {projection.numero_orden}")
            return projection.to_dict()

        except Exception as e:
            print(f"Error creating projection: {str(e)}")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Error creating projection.',
            )
