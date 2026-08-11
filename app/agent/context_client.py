import requests
from typing import Any

class EngineeringContextClient:

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    def get_endpoints(self) -> list[dict[str, Any]]:

        return self._get(
            "/engineering/endpoints",
        )

    def search_endpoints(
        self,
        keyword: str,
    ) -> list[dict[str, Any]]:

        return self._get(
            "/engineering/endpoints/search",
            params={
                "keyword": keyword,
            },
        )

    def get_endpoint_details(
        self,
        path: str,
    ) -> dict[str, Any]:

        return self._get(
            "/engineering/endpoints/details",
            params={
                "path": path,
            },
        )

    # ------------------------------------------------------------------
    # OpenAPI
    # ------------------------------------------------------------------

    def get_openapi(self) -> dict[str, Any]:

        return self._get(
            "/engineering/openapi",
        )

    # ------------------------------------------------------------------
    # Database entities
    # ------------------------------------------------------------------

    def get_entities(self) -> list[dict[str, Any]]:

        return self._get(
            "/engineering/entities",
        )

    def get_entity_details(
        self,
        table_name: str,
    ) -> dict[str, Any]:

        return self._get(
            "/engineering/entities/details",
            params={
                "table_name": table_name,
            },
        )

    # ------------------------------------------------------------------
    # Pydantic models
    # ------------------------------------------------------------------

    def get_models(self) -> list[dict[str, Any]]:

        return self._get(
            "/engineering/models",
        )

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def get_business_logic(
        self,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:

        return self._get_with_keywords(
            "/engineering/business-logic",
            keywords,
        )

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    def get_repositories(
        self,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:

        return self._get_with_keywords(
            "/engineering/repositories",
            keywords,
        )

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    def get_integrations(
        self,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:

        return self._get_with_keywords(
            "/engineering/integrations",
            keywords,
        )

    # ------------------------------------------------------------------
    # Documentation
    # ------------------------------------------------------------------

    def get_documentation(
        self,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:

        return self._get_with_keywords(
            "/engineering/documentation",
            keywords,
        )

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:

        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def _get_with_keywords(
        self,
        path: str,
        keywords: list[str] | None,
    ) -> Any:

        params = None

        if keywords:
            params = {
                "keywords": ",".join(keywords),
            }

        return self._get(
            path,
            params=params,
        )