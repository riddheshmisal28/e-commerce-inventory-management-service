from models import ApiMutation


ENDPOINT_RULES = [
    {
        "keywords": ["stock", "inventory", "quantity"],
        "path": "/skus",
        "method": "post",
        "change_type": "Request Payload Update",
        "details": "Support low_stock_threshold during SKU creation.",
    },
    {
        "keywords": ["stock", "inventory", "quantity"],
        "path": "/skus/{sku_id}",
        "method": "put",
        "change_type": "Request Payload Update",
        "details": "Allow updating low_stock_threshold configuration.",
    },
    {
        "keywords": ["stock", "inventory", "quantity"],
        "path": "/skus/product/{product_id}",
        "change_type": "Response Contract Update",
        "details": "Expose low stock status and threshold information.",
    },
    {
        "keywords": ["stock", "inventory", "quantity"],
        "path": "/products",
        "change_type": "Response Contract Update",
        "details": "Product listings may expose stock status.",
    },
    {
        "keywords": ["stock", "inventory", "quantity"],
        "path": "/products/{product_id}",
        "change_type": "Response Contract Update",
        "details": "Product details may expose stock status.",
    },
]


class EndpointAnalyzer:

    def analyze(
        self,
        requirement: str,
        endpoints: list,
    ) -> list[ApiMutation]:

        requirement = requirement.lower()
        impacts: list[ApiMutation] = []

        for endpoint in endpoints:

            path = endpoint["path"]

            methods = {
                method.lower()
                for method in endpoint["methods"]
            }

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

                required_method = rule.get("method")

                if required_method and required_method not in methods:
                    continue

                impacts.append(
                    ApiMutation(
                        endpoint=path,
                        change_type=rule["change_type"],
                        details=rule["details"],
                    )
                )

        return impacts

    def _matches_requirement(
        self,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        return any(
            keyword in requirement
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


def analyze_endpoints(
    requirement: str,
    endpoints: list,
) -> list[ApiMutation]:

    analyzer = EndpointAnalyzer()

    return analyzer.analyze(
        requirement,
        endpoints,
    )