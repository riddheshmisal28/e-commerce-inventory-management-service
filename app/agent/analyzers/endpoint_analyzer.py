def analyze_endpoints(
    requirement: str,
    endpoints: list
):
    impacts = []

    req = requirement.lower()

    if "stock" not in req:
        return impacts

    for endpoint in endpoints:

        path = endpoint["path"]
        methods = endpoint["methods"]

        # Ignore engineering endpoints
        if path.startswith("/engineering"):
            continue

        # Ignore category endpoints
        if path.startswith("/categories"):
            continue

        # SKU endpoints
        if path == "/skus":

            if "post" in methods:
                impacts.append({
                    "endpoint": path,
                    "change_type": "Request Payload Update",
                    "details": "Support low_stock_threshold during SKU creation."
                })

        elif path == "/skus/{sku_id}":

            if "put" in methods:
                impacts.append({
                    "endpoint": path,
                    "change_type": "Request Payload Update",
                    "details": "Allow updating low stock threshold configuration."
                })

        elif path == "/skus/product/{product_id}":

            impacts.append({
                "endpoint": path,
                "change_type": "Response Contract Update",
                "details": "Expose low stock status and threshold information."
            })

        elif path == "/products":

            impacts.append({
                "endpoint": path,
                "change_type": "Response Contract Update",
                "details": "Product listings may expose stock status."
            })

        elif path == "/products/{product_id}":

            impacts.append({
                "endpoint": path,
                "change_type": "Response Contract Update",
                "details": "Product details may expose stock status."
            })

    return impacts