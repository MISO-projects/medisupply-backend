from .db.database import engine, Base
from fastapi import FastAPI, Request, Depends
from .services.order_handler import OrderHandler
import base64
import json

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.post("/")
async def handle_command(request: Request, order_handler: OrderHandler = Depends()):
    envelope = await request.json()
    payload = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
    data = json.loads(payload)

    result = order_handler.handle_order(data)
    return {"data": result, "message": "Order handled successfully"}
