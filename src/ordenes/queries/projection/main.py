from .db.database import engine, Base
from fastapi import FastAPI, Request, Depends
from .services.order_projection_handler import OrderProjectionHandler
import base64
import json

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.post("/")
async def create_projection(
    request: Request, order_projection_handler: OrderProjectionHandler = Depends()
):
    try:
        envelope = await request.json()
        payload = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        data = json.loads(payload)

        result = order_projection_handler.handle_order_created_event(data)
        return {"data": result, "message": "Order handled successfully"}
    except Exception as e:
        print(f"Error creating projection: {str(e)}")
        raise e
