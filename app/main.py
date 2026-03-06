from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.product.api import router as product_router
from app.category.api import router as category_router
from app.sku.api import router as sku_router

from app.core.database import Base, engine
from app.product.exceptions import ProductException


def create_app() -> FastAPI:
    app = FastAPI(
        title="Inventory Management Service",
        version="1.0.0"
    )

    @app.exception_handler(ProductException)
    async def product_exception_handler(request: Request, exc: ProductException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message}
        )

    @app.on_event("startup")
    def startup_event():
        with engine.connect():
            pass

        Base.metadata.create_all(bind=engine)

    app.include_router(category_router)
    app.include_router(product_router)
    app.include_router(sku_router)

    return app


app = create_app()