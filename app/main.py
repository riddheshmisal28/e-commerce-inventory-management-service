from app.middleware.correlation_middleware import CorrelationIdMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.product.api import router as product_router
from app.category.api import router as category_router
from app.sku.api import router as sku_router

from app.core.database import Base, engine
from app.product.exceptions import ProductException
from app.core.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application startup...")
    try:
        with engine.connect():
            logger.info("Successfully connected to the database.")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema applied.")
    except Exception as e:
        logger.critical("Failed to connect and initialize database on startup!", extra={"error": str(e)}, exc_info=True)
    yield
    logger.info("Application shutdown successful.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Inventory Management Service",
        version="1.0.0",
        lifespan=lifespan
    )

    @app.exception_handler(ProductException)
    async def product_exception_handler(request: Request, exc: ProductException):
        logger.error("ProductException occurred", extra={"error_message": exc.message, "status_code": exc.status_code})
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message}
        )
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(category_router)
    app.include_router(product_router)
    app.include_router(sku_router)

    return app


app = create_app()