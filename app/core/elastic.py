from elasticsearch import Elasticsearch
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class ElasticSearchService:
    def __init__(self):
        self.client: Elasticsearch | None = None

    def connect(self):
        logger.info("Connecting to Elasticsearch...")
        try:
            self.client = Elasticsearch(settings.ELASTICSEARCH_URL)
            if self.client.ping():
                logger.info("Successfully connected to Elasticsearch.")
            else:
                logger.error("Could not ping Elasticsearch.")
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch", extra={"error": str(e)})
            raise

    def close(self):
        if self.client:
            logger.info("Closing Elasticsearch connection...")
            self.client.close()
            logger.info("Elasticsearch connection closed.")

    def get_client(self) -> Elasticsearch:
        if not self.client:
            raise Exception("Elasticsearch client is not initialized.")
        return self.client

es_service = ElasticSearchService()

def get_es_client() -> Elasticsearch:
    return es_service.get_client()
