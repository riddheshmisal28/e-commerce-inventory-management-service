class ProductException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ProductNotFound(ProductException):
    def __init__(self, message: str = "Product not found"):
        super().__init__(message, status_code=404)

class CategoryNotFound(ProductException):
    def __init__(self, message: str = "Category not found"):
        super().__init__(message, status_code=404)