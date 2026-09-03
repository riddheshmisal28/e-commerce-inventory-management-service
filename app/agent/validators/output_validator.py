"""
Output Guardrails / Validation Module

Provides comprehensive output guardrails for the impact analysis agent.

Validates:
- Output schema and required fields
- Requirement-to-impact alignment
- Evidence grounding
- Confidence values
- Speculative impacts
- Cross-section consistency
- Blast-radius consistency
- Duplicate impacts
- Invalid / contradictory output

The output validator is intentionally deterministic and does not make
additional LLM calls. Its purpose is to prevent unsupported or malformed
analysis from reaching the final user.
"""

from dataclasses import dataclass
from typing import Any, Optional
import re

from app.agent.models import (
    Requirement,
    ImpactAnalysisReport,
    AnalysisContext,
)
from app.agent.core.agent_step import AgentStep
from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class OutputValidationError:
    """Represents an output validation issue."""

    category: str
    message: str
    severity: str = "error"  # error, warning


class OutputValidator(AgentStep):
    """
    Validates the final ImpactAnalysisReport before it is returned.

    Validation areas:
    - Schema validity
    - Requirement alignment
    - Evidence grounding
    - Confidence
    - Speculation
    - Duplicate impacts
    - Cross-section consistency
    - Blast-radius consistency
    """

    name = "Output Validator"
    required_context: set[str] = set()

    # =========================================================
    # CONFIGURATION
    # =========================================================

    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0

    MIN_RELEVANCE_SCORE = 0.0
    MAX_RELEVANCE_SCORE = 1.0

    # Impacts containing these terms require particularly strong
    # evidence because they generally imply architectural/data changes.
    HIGH_RISK_CHANGE_TERMS = {
        "add table",
        "create table",
        "new table",
        "add column",
        "create column",
        "new column",
        "add field",
        "create field",
        "new field",
        "new endpoint",
        "create endpoint",
        "new api",
        "create api",
        "new service",
        "create service",
        "new integration",
        "payment gateway",
        "database migration",
        "schema migration",
    }

    SPECULATIVE_TERMS = {
        "might",
        "may",
        "could",
        "possibly",
        "potentially",
        "perhaps",
        "assume",
        "assuming",
        "likely",
        "probably",
        "could require",
        "might require",
        "may require",
    }

    # Change types that generally need stronger evidence.
    STRUCTURAL_CHANGE_TYPES = {
        "SCHEMA_CHANGE",
        "NEW_ENTITY",
        "API_CHANGE",
        "API_MUTATION",
        "MODEL_CHANGE",
        "REPOSITORY_CHANGE",
        "INTEGRATION_CHANGE",
    }

    # =========================================================
    # PUBLIC API
    # =========================================================

    def execute(self, ctx: AnalysisContext) -> None:
        """Validate the report assembled by the preceding Report Builder step."""
        is_valid, errors = self.validate(ctx.report, ctx.requirement)
        validation_summary = {
            "valid": is_valid,
            "error_count": sum(error.severity == "error" for error in errors),
            "warning_count": sum(error.severity == "warning" for error in errors),
            "errors": [
                {
                    "category": error.category,
                    "message": error.message,
                    "severity": error.severity,
                }
                for error in errors
            ],
        }
        ctx.metadata["output_validation"] = validation_summary

        if not is_valid:
            messages = "; ".join(
                f"[{error.category}] {error.message}"
                for error in errors
                if error.severity == "error"
            )
            raise ValueError(f"Output validation failed: {messages}")

    def validate(
        self,
        report: ImpactAnalysisReport,
        requirement: Requirement,
    ) -> tuple[bool, list[OutputValidationError]]:
        """
        Validate the complete impact analysis report.

        Args:
            report:
                Final ImpactAnalysisReport produced by the agent.

            requirement:
                Original validated requirement.

        Returns:
            Tuple of:
                - bool: True if no blocking errors were found
                - list[OutputValidationError]: validation issues
        """

        errors: list[OutputValidationError] = []

        if report is None:
            errors.append(
                OutputValidationError(
                    category="schema",
                    message="Impact analysis report is missing",
                    severity="error",
                )
            )
            return False, errors

        # Run all output validations.
        errors.extend(self._validate_schema(report))
        errors.extend(
            self._validate_requirement_alignment(
                report,
                requirement,
            )
        )
        errors.extend(self._validate_evidence(report))
        errors.extend(self._validate_confidence(report))
        errors.extend(self._validate_speculative_impacts(report))
        errors.extend(self._validate_duplicates(report))
        errors.extend(self._validate_cross_section_consistency(report))
        errors.extend(self._validate_blast_radius(report))

        is_valid = not any(
            error.severity == "error"
            for error in errors
        )

        if is_valid:
            logger.info(
                "Output guardrail validation passed",
                extra={
                    "warning_count": sum(
                        1
                        for error in errors
                        if error.severity == "warning"
                    )
                },
            )
        else:
            logger.warning(
                "Output guardrail validation failed",
                extra={
                    "error_count": sum(
                        1
                        for error in errors
                        if error.severity == "error"
                    ),
                    "warning_count": sum(
                        1
                        for error in errors
                        if error.severity == "warning"
                    ),
                },
            )

        return is_valid, errors

    # =========================================================
    # SCHEMA VALIDATION
    # =========================================================

    def _validate_schema(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Validate basic report structure and values.

        Pydantic should perform most structural validation. This method
        handles additional semantic checks that are not necessarily
        covered by the model schema.
        """

        errors: list[OutputValidationError] = []

        required_sections = [
            "feature_summary",
            "component_blast_radius",
            "data_model_impact",
            "api_interface_mutations",
            "model_impacts",
            "business_logic_impacts",
            "repository_impacts",
            "integration_impacts",
            "component_impacts",
            "clarification_questions",
            "test_scenarios",
            "bdd_scenarios",
        ]

        for section in required_sections:
            if not hasattr(report, section):
                errors.append(
                    OutputValidationError(
                        category="schema",
                        message=f"Required report section is missing: {section}",
                        severity="error",
                    )
                )

        # Validate impact collections.
        impact_sections = [
            "data_model_impact",
            "api_interface_mutations",
            "model_impacts",
            "business_logic_impacts",
            "repository_impacts",
            "integration_impacts",
            "component_impacts",
        ]

        for section in impact_sections:
            impacts = getattr(report, section, None)

            if impacts is None:
                continue

            if not isinstance(impacts, list):
                errors.append(
                    OutputValidationError(
                        category="schema",
                        message=(
                            f"Impact section '{section}' must be a list"
                        ),
                        severity="error",
                    )
                )

        return errors

    # =========================================================
    # REQUIREMENT ALIGNMENT
    # =========================================================

    def _validate_requirement_alignment(
        self,
        report: ImpactAnalysisReport,
        requirement: Requirement,
    ) -> list[OutputValidationError]:
        """
        Detect impacts that are clearly unrelated to the requirement.

        This is intentionally conservative. Lack of keyword overlap is
        treated as a warning rather than an automatic rejection because
        semantic relationships may not use identical terminology.
        """

        errors: list[OutputValidationError] = []

        if requirement is None:
            return errors

        requirement_text = self._normalize_text(
            " ".join(
                [
                    requirement.title or "",
                    requirement.description or "",
                    " ".join(requirement.acceptance_criteria or []),
                ]
            )
        )

        requirement_terms = self._extract_terms(requirement_text)

        for section_name, impacts in self._get_impact_sections(report):
            for index, impact in enumerate(impacts):
                impact_text = self._impact_to_text(impact)

                if not impact_text:
                    errors.append(
                        OutputValidationError(
                            category="requirement_alignment",
                            message=(
                                f"{section_name}[{index}] contains an "
                                "empty impact description"
                            ),
                            severity="error",
                        )
                    )
                    continue

                impact_terms = self._extract_terms(impact_text)

                # If there is no meaningful overlap at all, flag it.
                # This is a warning because semantic relationships may
                # not share exact vocabulary.
                overlap = requirement_terms.intersection(impact_terms)

                if not overlap:
                    errors.append(
                        OutputValidationError(
                            category="requirement_alignment",
                            message=(
                                f"{section_name}[{index}] has no obvious "
                                "lexical alignment with the requirement: "
                                f"{impact_text[:180]}"
                            ),
                            severity="warning",
                        )
                    )

        return errors

    # =========================================================
    # EVIDENCE VALIDATION
    # =========================================================

    def _validate_evidence(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Validate evidence attached to generated impacts.

        High-confidence impacts should have evidence.
        Structural changes require particularly strong evidence.
        """

        errors: list[OutputValidationError] = []

        for section_name, impacts in self._get_impact_sections(report):
            for index, impact in enumerate(impacts):
                evidence = getattr(impact, "evidence", None)

                if evidence is None:
                    errors.append(
                        OutputValidationError(
                            category="evidence",
                            message=(
                                f"{section_name}[{index}] has no evidence"
                            ),
                            severity="error",
                        )
                    )
                    continue

                if not isinstance(evidence, list):
                    errors.append(
                        OutputValidationError(
                            category="evidence",
                            message=(
                                f"{section_name}[{index}] evidence must "
                                "be a list"
                            ),
                            severity="error",
                        )
                    )
                    continue

                usable_evidence = [
                    item
                    for item in evidence
                    if item is not None
                    and str(item).strip()
                ]

                if not usable_evidence:
                    errors.append(
                        OutputValidationError(
                            category="evidence",
                            message=(
                                f"{section_name}[{index}] contains an "
                                "empty evidence list"
                            ),
                            severity="error",
                        )
                    )

                confidence = self._get_numeric_field(
                    impact,
                    "confidence",
                )

                change_type = str(
                    getattr(
                        impact,
                        "change_type",
                        "",
                    )
                ).upper()

                # High confidence without evidence is invalid.
                if (
                    confidence is not None
                    and confidence >= 0.8
                    and not usable_evidence
                ):
                    errors.append(
                        OutputValidationError(
                            category="evidence",
                            message=(
                                f"{section_name}[{index}] has high "
                                f"confidence ({confidence}) but no "
                                "supporting evidence"
                            ),
                            severity="error",
                        )
                    )

                # Structural changes should always have evidence.
                if (
                    change_type in self.STRUCTURAL_CHANGE_TYPES
                    and not usable_evidence
                ):
                    errors.append(
                        OutputValidationError(
                            category="evidence",
                            message=(
                                f"{section_name}[{index}] is a structural "
                                f"change ({change_type}) without evidence"
                            ),
                            severity="error",
                        )
                    )

        return errors

    # =========================================================
    # CONFIDENCE VALIDATION
    # =========================================================

    def _validate_confidence(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Validate confidence and relevance scores.
        """

        errors: list[OutputValidationError] = []

        for section_name, impacts in self._get_impact_sections(report):
            for index, impact in enumerate(impacts):

                confidence = self._get_numeric_field(
                    impact,
                    "confidence",
                )

                if confidence is not None:
                    if not (
                        self.MIN_CONFIDENCE
                        <= confidence
                        <= self.MAX_CONFIDENCE
                    ):
                        errors.append(
                            OutputValidationError(
                                category="confidence",
                                message=(
                                    f"{section_name}[{index}] confidence "
                                    f"must be between 0 and 1, got "
                                    f"{confidence}"
                                ),
                                severity="error",
                            )
                        )

                relevance_score = self._get_numeric_field(
                    impact,
                    "relevance_score",
                )

                if relevance_score is not None:
                    if not (
                        self.MIN_RELEVANCE_SCORE
                        <= relevance_score
                        <= self.MAX_RELEVANCE_SCORE
                    ):
                        errors.append(
                            OutputValidationError(
                                category="confidence",
                                message=(
                                    f"{section_name}[{index}] relevance "
                                    f"score must be between 0 and 1, got "
                                    f"{relevance_score}"
                                ),
                                severity="error",
                            )
                        )

                # Perfect confidence deserves explicit evidence.
                if (
                    confidence is not None
                    and confidence >= 0.99
                ):
                    evidence = getattr(
                        impact,
                        "evidence",
                        None,
                    )

                    if not evidence:
                        errors.append(
                            OutputValidationError(
                                category="confidence",
                                message=(
                                    f"{section_name}[{index}] reports "
                                    "near-perfect confidence without "
                                    "evidence"
                                ),
                                severity="error",
                            )
                        )

        return errors

    # =========================================================
    # SPECULATION VALIDATION
    # =========================================================

    def _validate_speculative_impacts(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Detect impacts that appear speculative.

        The validator does not blindly reject every uncertain statement.
        It flags speculative language and structural assumptions so that
        the final pipeline can decide whether to downgrade/remove them.
        """

        errors: list[OutputValidationError] = []

        for section_name, impacts in self._get_impact_sections(report):
            for index, impact in enumerate(impacts):

                impact_text = self._normalize_text(
                    self._impact_to_text(impact)
                )

                matched_terms = [
                    term
                    for term in self.SPECULATIVE_TERMS
                    if term in impact_text
                ]

                if matched_terms:
                    confidence = self._get_numeric_field(
                        impact,
                        "confidence",
                    )

                    # Speculative language + high confidence is suspicious.
                    if confidence is not None and confidence >= 0.8:
                        errors.append(
                            OutputValidationError(
                                category="speculation",
                                message=(
                                    f"{section_name}[{index}] uses "
                                    f"speculative language "
                                    f"({', '.join(matched_terms)}) but has "
                                    f"high confidence ({confidence})"
                                ),
                                severity="warning",
                            )
                        )

                # Structural changes need stronger evidence.
                if self._contains_high_risk_change(impact_text):
                    evidence = getattr(
                        impact,
                        "evidence",
                        None,
                    )

                    if not evidence:
                        errors.append(
                            OutputValidationError(
                                category="speculation",
                                message=(
                                    f"{section_name}[{index}] proposes a "
                                    "potential structural change without "
                                    "supporting evidence"
                                ),
                                severity="error",
                            )
                        )

        return errors

    # =========================================================
    # DUPLICATE VALIDATION
    # =========================================================

    def _validate_duplicates(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Detect duplicate impacts within the same section.
        """

        errors: list[OutputValidationError] = []

        for section_name, impacts in self._get_impact_sections(report):
            seen: dict[str, int] = {}

            for index, impact in enumerate(impacts):
                fingerprint = self._impact_fingerprint(impact)

                if not fingerprint:
                    continue

                if fingerprint in seen:
                    errors.append(
                        OutputValidationError(
                            category="duplicates",
                            message=(
                                f"{section_name}[{index}] duplicates "
                                f"{section_name}[{seen[fingerprint]}]"
                            ),
                            severity="warning",
                        )
                    )
                else:
                    seen[fingerprint] = index

        return errors

    # =========================================================
    # CROSS SECTION CONSISTENCY
    # =========================================================

    def _validate_cross_section_consistency(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Detect contradictions between report sections.

        Examples:
        - BUSINESS_RULE impact classified as a database schema change.
        - API mutation absent but API layer claimed as impacted.
        - No model impact but report claims model changes.
        """

        errors: list[OutputValidationError] = []

        data_model_impacts = getattr(
            report,
            "data_model_impact",
            [],
        ) or []

        api_impacts = getattr(
            report,
            "api_interface_mutations",
            [],
        ) or []

        model_impacts = getattr(
            report,
            "model_impacts",
            [],
        ) or []

        repository_impacts = getattr(
            report,
            "repository_impacts",
            [],
        ) or []

        integration_impacts = getattr(
            report,
            "integration_impacts",
            [],
        ) or []

        component_impacts = getattr(
            report,
            "component_impacts",
            [],
        ) or []

        blast_radius = getattr(
            report,
            "component_blast_radius",
            [],
        ) or []

        # -----------------------------------------------------
        # BUSINESS RULE vs DATABASE
        # -----------------------------------------------------

        for index, impact in enumerate(data_model_impacts):
            change_type = str(
                getattr(
                    impact,
                    "change_type",
                    "",
                )
            ).upper()

            change_text = self._normalize_text(
                str(
                    getattr(
                        impact,
                        "change",
                        "",
                    )
                )
            )

            if change_type == "BUSINESS_RULE":
                if any(
                    term in change_text
                    for term in (
                        "add column",
                        "new column",
                        "create column",
                        "add table",
                        "new table",
                        "database migration",
                        "schema migration",
                    )
                ):
                    errors.append(
                        OutputValidationError(
                            category="consistency",
                            message=(
                                f"data_model_impact[{index}] is classified "
                                "as BUSINESS_RULE but describes a "
                                "structural database change"
                            ),
                            severity="error",
                        )
                    )

        # -----------------------------------------------------
        # API CONSISTENCY
        # -----------------------------------------------------

        blast_text = self._normalize_text(
            " ".join(
                self._impact_to_text(item)
                for item in blast_radius
            )
        )

        if "api" in blast_text and not api_impacts:
            errors.append(
                OutputValidationError(
                    category="consistency",
                    message=(
                        "Blast radius references API impact, but "
                        "api_interface_mutations is empty"
                    ),
                    severity="warning",
                )
            )

        if "model" in blast_text and not model_impacts:
            errors.append(
                OutputValidationError(
                    category="consistency",
                    message=(
                        "Blast radius references model impact, but "
                        "model_impacts is empty"
                    ),
                    severity="warning",
                )
            )

        if "repository" in blast_text and not repository_impacts:
            errors.append(
                OutputValidationError(
                    category="consistency",
                    message=(
                        "Blast radius references repository impact, but "
                        "repository_impacts is empty"
                    ),
                    severity="warning",
                )
            )

        if (
            "integration" in blast_text
            and not integration_impacts
        ):
            errors.append(
                OutputValidationError(
                    category="consistency",
                    message=(
                        "Blast radius references integration impact, but "
                        "integration_impacts is empty"
                    ),
                    severity="warning",
                )
            )

        if (
            "component" in blast_text
            and not component_impacts
        ):
            errors.append(
                OutputValidationError(
                    category="consistency",
                    message=(
                        "Blast radius references component impact, but "
                        "component_impacts is empty"
                    ),
                    severity="warning",
                )
            )

        return errors

    # =========================================================
    # BLAST RADIUS VALIDATION
    # =========================================================

    def _validate_blast_radius(
        self,
        report: ImpactAnalysisReport,
    ) -> list[OutputValidationError]:
        """
        Validate blast-radius entries.

        Important distinction:

        BUSINESS_RULE impact
            !=
        DATABASE_SCHEMA_CHANGE

        The blast-radius description should not imply a migration when
        the underlying impact only represents a business-rule change.
        """

        errors: list[OutputValidationError] = []

        blast_radius = getattr(
            report,
            "component_blast_radius",
            [],
        ) or []

        data_model_impacts = getattr(
            report,
            "data_model_impact",
            [],
        ) or []

        has_schema_change = any(
            str(
                getattr(
                    impact,
                    "change_type",
                    "",
                )
            ).upper()
            in {
                "SCHEMA_CHANGE",
                "NEW_ENTITY",
            }
            for impact in data_model_impacts
        )

        for index, blast in enumerate(blast_radius):
            component = self._normalize_text(
                str(
                    getattr(
                        blast,
                        "component",
                        "",
                    )
                )
            )

            reason = self._normalize_text(
                str(
                    getattr(
                        blast,
                        "reason",
                        "",
                    )
                )
            )

            database_language = (
                "database" in component
                or "database" in reason
                or "migration" in reason
                or "schema" in reason
            )

            if database_language and not has_schema_change:
                # Database/entity wording can be legitimate, but if
                # there is no structural schema impact we should avoid
                # implying that a migration is required.
                errors.append(
                    OutputValidationError(
                        category="blast_radius",
                        message=(
                            f"component_blast_radius[{index}] may imply "
                            "a database/schema change although no "
                            "SCHEMA_CHANGE or NEW_ENTITY impact exists"
                        ),
                        severity="warning",
                    )
                )

            severity = str(
                getattr(
                    blast,
                    "severity",
                    "",
                )
            ).strip()

            if severity and severity not in {
                "Low",
                "Medium",
                "High",
                "Critical",
            }:
                errors.append(
                    OutputValidationError(
                        category="blast_radius",
                        message=(
                            f"component_blast_radius[{index}] has "
                            f"invalid severity: {severity}"
                        ),
                        severity="error",
                    )
                )

        return errors

    # =========================================================
    # IMPACT SECTION HELPERS
    # =========================================================

    def _get_impact_sections(
        self,
        report: ImpactAnalysisReport,
    ) -> list[tuple[str, list[Any]]]:
        """Return all impact sections in a consistent format."""

        sections: list[tuple[str, list[Any]]] = []

        section_names = [
            "data_model_impact",
            "api_interface_mutations",
            "model_impacts",
            "business_logic_impacts",
            "repository_impacts",
            "integration_impacts",
            "component_impacts",
        ]

        for section_name in section_names:
            impacts = getattr(
                report,
                section_name,
                None,
            )

            if impacts is None:
                continue

            if not isinstance(impacts, list):
                continue

            sections.append(
                (
                    section_name,
                    impacts,
                )
            )

        return sections

    # =========================================================
    # TEXT / FINGERPRINT HELPERS
    # =========================================================

    def _impact_to_text(self, impact: Any) -> str:
        """
        Convert an impact object into searchable text.
        """

        if impact is None:
            return ""

        fields = [
            "entity",
            "component",
            "change_type",
            "change",
            "reason",
            "description",
            "endpoint",
            "model",
            "repository",
            "integration",
            "service",
            "name",
        ]

        values: list[str] = []

        for field in fields:
            value = getattr(
                impact,
                field,
                None,
            )

            if value is not None:
                values.append(str(value))

        return " ".join(values)

    def _impact_fingerprint(
        self,
        impact: Any,
    ) -> str:
        """
        Generate a normalized fingerprint for duplicate detection.
        """

        text = self._normalize_text(
            self._impact_to_text(impact)
        )

        if not text:
            return ""

        return text

    def _normalize_text(
        self,
        text: str,
    ) -> str:
        """Normalize text for comparisons."""

        if not text:
            return ""

        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", " ", text)

        return text.strip()

    def _extract_terms(
        self,
        text: str,
    ) -> set[str]:
        """
        Extract meaningful terms for lightweight alignment checks.

        This is intentionally not a semantic similarity engine. Semantic
        matching should continue to be handled by the agent's retrieval
        / reasoning layer.
        """

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "for",
            "in",
            "on",
            "with",
            "is",
            "are",
            "be",
            "as",
            "by",
            "when",
            "then",
            "this",
            "that",
            "from",
            "into",
            "must",
            "should",
            "will",
        }

        words = set(
            self._normalize_text(text).split()
        )

        return {
            word
            for word in words
            if len(word) > 2
            and word not in stop_words
        }

    def _get_numeric_field(
        self,
        obj: Any,
        field_name: str,
    ) -> Optional[float]:
        """Safely read and convert a numeric field."""

        value = getattr(
            obj,
            field_name,
            None,
        )

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _contains_high_risk_change(
        self,
        text: str,
    ) -> bool:
        """Check whether an impact describes a structural change."""

        normalized = self._normalize_text(text)

        return any(
            term in normalized
            for term in self.HIGH_RISK_CHANGE_TERMS
        )

    # =========================================================
    # REPORT GENERATION
    # =========================================================

    def get_validation_report(
        self,
        report: ImpactAnalysisReport,
        requirement: Requirement,
    ) -> dict:
        """
        Return a structured output guardrail report.
        """

        is_valid, errors = self.validate(
            report,
            requirement,
        )

        errors_by_category: dict[str, list[str]] = {}
        warnings: list[str] = []
        critical_issues: list[str] = []

        for error in errors:
            if error.severity == "error":
                errors_by_category.setdefault(
                    error.category,
                    [],
                ).append(error.message)

                critical_issues.append(
                    f"[{error.category.upper()}] {error.message}"
                )
            else:
                warnings.append(
                    f"[{error.category.upper()}] {error.message}"
                )

        error_count = sum(
            1
            for error in errors
            if error.severity == "error"
        )

        warning_count = sum(
            1
            for error in errors
            if error.severity == "warning"
        )

        return {
            "valid": is_valid,
            "summary": (
                "✓ Valid output"
                if is_valid
                else "✗ Invalid output"
            ),
            "error_count": error_count,
            "warning_count": warning_count,
            "critical_issues": critical_issues,
            "errors_by_category": errors_by_category,
            "warnings": warnings,
        }