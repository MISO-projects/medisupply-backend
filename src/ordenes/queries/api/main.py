from fastapi import FastAPI, Request, HTTPException
from .router.order_router import order_router

app = FastAPI()


app.include_router(router=order_router, prefix='/orders')
