from models import (
    AnalysisContext,
    BlastRadius,
)


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
        ctx: AnalysisContext,
    ) -> None:

        blast_radius: list[BlastRadius] = []

        for rule in BLAST_RADIUS_RULES:

            if (
                rule["source"] == "entity"
                and ctx.entity_impacts
            ):

                blast_radius.append(
                    BlastRadius(
                        component=rule["component"],
                        reason=rule["reason"],
                    )
                )

            elif (
                rule["source"] == "endpoint"
                and ctx.endpoint_impacts
            ):

                blast_radius.append(
                    BlastRadius(
                        component=rule["component"],
                        reason=rule["reason"],
                    )
                )

        ctx.blast_radius = blast_radius