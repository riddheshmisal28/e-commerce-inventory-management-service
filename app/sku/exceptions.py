from app.product.exceptions import ProductException

class SKUNotFound(ProductException):
    def __init__(self, message: str = "SKU not found"):
        super().__init__(message, status_code = 404)

class SKUAlreadyExists(ProductException):
    def __init__(self, message: str = "SKU code already exists"):
        super().__init__(message, status_code = 400)