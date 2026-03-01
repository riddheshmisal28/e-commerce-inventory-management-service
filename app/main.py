from fastapi import FastAPI
from app.product.api import router as product_router

def create_app() -> FastAPI:
    app = FastAPI(
        title = "Inventory Management Service",
        version = "1.0.0"
    )

    app.include_router(product_router)

    return app

app = create_app()