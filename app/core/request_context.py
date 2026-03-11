from contextvars import ContextVar

correlation_id_ctx = ContextVar("correlation_id", default = None)

def get_correlation_id():
    return correlation_id_ctx.get()

def set_correlation_id(correlation_id: str):
    correlation_id_ctx.set(correlation_id)