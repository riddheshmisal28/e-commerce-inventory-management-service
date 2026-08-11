from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ApiMutation,
)

ENDPOINT_RULES = [
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "path": "/skus",
        "method": "post",
        "change_type": "Request Payload Update",
        "details": (
            "Support low_stock_threshold during SKU creation."
        ),
    },
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "path": "/skus/{sku_id}",
        "method": "put",
        "change_type": "Request Payload Update",
        "details": (
            "Allow updating low_stock_threshold configuration."
        ),
    },
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "path": "/skus/product/{product_id}",
        "change_type": "Response Contract Update",
        "details": (
            "Expose low stock status and threshold information."
        ),
    },
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "path": "/products",
        "change_type": "Response Contract Update",
        "details": (
            "Product listings may expose stock status."
        ),
    },
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "path": "/products/{product_id}",
        "change_type": "Response Contract Update",
        "details": (
            "Product details may expose stock status."
        ),
    }
]

class EndpointAnalyzer(AgentStep):

    name = "Endpoint Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        requirement = ctx.requirement_text

        impacts: list[ApiMutation] = []

        for endpoint in ctx.engineering_context.endpoints:

            path = endpoint.get(
                "path",
                "",
            )

            methods = {
                method.lower()
                for method in endpoint.get(
                    "methods",
                    [],
                )
            }

            if not path:
                continue

            if self._ignore_endpoint(path):
                continue

            for rule in ENDPOINT_RULES:

                if not self._matches_requirement(
                    requirement,
                    rule["keywords"],
                ):
                    continue

                if path != rule["path"]:
                    continue

                required_method = rule.get(
                    "method",
                )

                if (
                    required_method
                    and required_method not in methods
                ):
                    continue

                impacts.append(
                    ApiMutation(
                        endpoint=path,
                        change_type=rule["change_type"],
                        details=rule["details"],
                    )
                )

        ctx.endpoint_impacts = self._deduplicate_impacts(
            impacts,
        )

    def _matches_requirement(
        self,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        return any(
            keyword.lower() in requirement
            for keyword in keywords
        )

    def _ignore_endpoint(
        self,
        path: str,
    ) -> bool:

        return (
            path.startswith("/engineering")
            or path.startswith("/categories")
        )

    def _deduplicate_impacts(
        self,
        impacts: list[ApiMutation],
    ) -> list[ApiMutation]:

        seen: set[tuple[str, str, str]] = set()

        unique_impacts: list[ApiMutation] = []

        for impact in impacts:

            key = (
                impact.endpoint,
                impact.change_type,
                impact.details,
            )

            if key in seen:
                continue

            seen.add(key)
            unique_impacts.append(impact)

        return unique_impacts