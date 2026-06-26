def build_blast_radius(
    entity_impacts,
    endpoint_impacts
):
    components = []

    if entity_impacts:
        components.append({
            "component": "SKU Service",
            "reason":
                "Inventory quantity and threshold logic are maintained at SKU level."
        })

    if endpoint_impacts:
        components.append({
            "component": "Inventory APIs",
            "reason":
                "SKU and Product endpoints may require contract changes."
        })

    return components