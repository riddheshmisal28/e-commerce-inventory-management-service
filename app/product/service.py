from app.category.repository import CategoryRepository
from .exceptions import ProductNotFound, CategoryNotFound
from uuid import uuid4
from .repository import ProductRepository
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.core.elastic import get_es_client
from elasticsearch import helpers
from .model import Product

logger = get_logger(__name__)

class ProductService:
    def __init__(self, db: Session): 
        self.repo = ProductRepository(db)
        self.category_repo = CategoryRepository()

    def create_product(self, db: Session, data):
        logger.info("Starting product creation", extra={"product_name": data.name, "category_id": str(data.category_id)})
        category = self.category_repo.get_by_id(db, data.category_id)
        if not category:
            logger.error("Product creation failed - Category not found", extra={"category_id": str(data.category_id)})
            raise CategoryNotFound("Category not found")
        product = Product(
            name = data.name,
            description = data.description,
            category_id = data.category_id
        )

        created = self.repo.create(product)

        try:
            es = get_es_client()
            es.index(
                index="products",
                id=str(created.id),
                document={
                    "name": created.name,
                    "description": created.description,
                    "category_id": str(created.category_id)
                }
            )
            logger.info("Product indexed in Elasticsearch successfully", extra={"product_id": str(created.id)})
        except Exception as e:
            logger.error("Failed to index product in ES", extra={"error": str(e), "product_id": str(created.id)})

        logger.info("Product created successfully", extra={"product_id": str(created.id), "category_id": str(created.category_id)})
        return created

    def get_product(self, product_id):
        product = self.repo.get(product_id)
        if not product:
            logger.warning("Product lookup failed - not found", extra={"product_id": str(product_id)})
            raise ProductNotFound("Product not found")
        return product

    def delete_product(self, product_id):
        logger.info("Starting product deletion", extra={"product_id": str(product_id)})
        product = self.get_product(product_id)
        self.repo.delete(product)

        try:
            es = get_es_client()
            es.delete(index="products", id=str(product_id), ignore_status=[404])
            logger.info("Product deleted from Elasticsearch successfully", extra={"product_id": str(product_id)})
        except Exception as e:
            logger.error("Failed to delete product from ES", extra={"error": str(e), "product_id": str(product_id)})

        logger.info("Product deleted successfully", extra={"product_id": str(product_id)})

    def list_products(self, search, category_id, page, page_size):
        logger.info("Listing products", extra={"search": search, "category_id": str(category_id) if category_id else None, "page": page, "page_size": page_size})
        products, total = self.repo.list(search, category_id, page, page_size)
        logger.info("Products listed successfully", extra={"total_results": total, "retrieved_count": len(products)})
        return products, total

    def sync_all_products(self):
        logger.info("Starting bulk sync of products to Elasticsearch")
        products = self.repo.get_all()
        if not products:
            logger.info("No products found to sync")
            return 0
        
        es = get_es_client()
        
        def generate_actions():
            for product in products:
                yield {
                    "_index": "products",
                    "_id": str(product.id),
                    "_source": {
                        "name": product.name,
                        "description": product.description,
                        "category_id": str(product.category_id)
                    }
                }
                
        try:
            success, failed = helpers.bulk(es, generate_actions(), stats_only=True)
            logger.info("Bulk sync completed", extra={"successful": success, "failed": failed})
            return success
        except Exception as e:
            logger.error("Failed during bulk sync to ES", extra={"error": str(e)})
            raise e

    def search_products(self, query: str):
        logger.info("Searching products in Elasticsearch", extra={"query": query})
        if not query:
            return []
            
        try:
            es = get_es_client()
            response = es.search(
                index="products",
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^3", "description"]
                        }
                    }
                }
            )
            hits = response.get("hits", {}).get("hits", [])
            results = []
            for hit in hits:
                source = hit["_source"]
                results.append({
                    "id": hit["_id"],
                    "name": source.get("name"),
                    "description": source.get("description", ""),
                    "category_id": source.get("category_id")
                })
            
            logger.info("Search successful", extra={"query": query, "results_count": len(results)})
            return results
        except Exception as e:
            logger.error("Failed to search products in ES", extra={"error": str(e)})
            raise e