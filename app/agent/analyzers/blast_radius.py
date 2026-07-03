from models import BlastRadius


BLAST_RADIUS_RULES = [
    {
        "source": "entity",
        "component": "SKU Service",
        "reason": "Inventory quantity and threshold logic are maintained at SKU level.",
    },
    {
        "source": "endpoint",
        "component": "Inventory APIs",
        "reason": "SKU and Product endpoints may require contract changes.",
    },
]


class BlastRadiusAnalyzer:

    def analyze(
        self,
        entity_impacts,
        endpoint_impacts,
    ) -> list[BlastRadius]:

        blast_radius = []

        for rule in BLAST_RADIUS_RULES:

            if (
                rule["source"] == "entity"
                and entity_impacts
            ):

                blast_radius.append(
                    BlastRadius(
                        component=rule["component"],
                        reason=rule["reason"],
                    )
                )

            elif (
                rule["source"] == "endpoint"
                and endpoint_impacts
            ):

                blast_radius.append(
                    BlastRadius(
                        component=rule["component"],
                        reason=rule["reason"],
                    )
                )

        return blast_radius


def build_blast_radius(
    entity_impacts,
    endpoint_impacts,
):

    analyzer = BlastRadiusAnalyzer()

    return analyzer.analyze(
        entity_impacts,
        endpoint_impacts,
    )