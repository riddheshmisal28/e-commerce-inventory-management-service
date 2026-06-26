def analyze_entities(
    requirement: str,
    entities: list
):
    impacts = []

    req = requirement.lower()

    for entity in entities:

        entity_name = entity["name"]

        columns = [
            c.lower()
            for c in entity["columns"]
        ]

        if "stock" in req:

            if "quantity" in columns:
                impacts.append(
                    {
                        "entity": entity_name,
                        "change":
                            "Inventory quantity tracking exists. Low stock alert evaluation logic may be required."
                    }
                )

                impacts.append(
                    {
                        "entity": entity_name,
                        "change":
                            "Consider adding low_stock_threshold configuration."
                    }
                )

                impacts.append(
                    {
                        "entity": entity_name,
                        "change":
                            "Consider storing last_alert_timestamp to avoid duplicate notifications."
                    }
                )

    return impacts