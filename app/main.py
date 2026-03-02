from fastapi import FastAPI
from app.product.api import router as product_router
from app.core.database import Base, engine

def create_app() -> FastAPI:
    app = FastAPI(
        title = "Inventory Management Service",
        version = "1.0.0"
    )
    Base.metadata.create_all(bind=engine)

    app.include_router(product_router)

    return app

app = create_app()