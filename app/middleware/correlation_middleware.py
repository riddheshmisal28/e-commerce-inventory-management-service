from app.core.request_context import set_correlation_id
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger
import time

logger = get_logger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))
        set_correlation_id(correlation_id)
        
        start_time = time.time()
        logger.info("Incoming request", extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None
        })
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info("Request completed", extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2)
        })
        
        response.headers["X-Correlation-Id"] = correlation_id
        return response