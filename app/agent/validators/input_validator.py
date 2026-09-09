"""
Input Validation Module

Provides comprehensive input guardrails to protect the agent from:
- Prompt injection attacks
- Vague/malformed requirements
- Information leakage (PII, credentials)
- Off-topic or irrelevant inputs
- Resource exhaustion attacks
"""

import re
from typing import Optional
from dataclasses import dataclass

from app.agent.models import Requirement
from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error with category and message."""
    category: str
    message: str
    severity: str = "error"  # "error", "warning"


class InputValidator:
    """
    Comprehensive input validator for requirements.
    
    Validates against:
    - Prompt injection patterns
    - Input length and complexity
    - Domain relevance
    - Sensitive information leakage
    - Vagueness indicators
    """

    # =========================================================
    # INJECTION PATTERNS
    # =========================================================
    
    INJECTION_PATTERNS = [
        # System prompt manipulation
        r'(?i)(ignore|override|bypass|escape).*(?:instruction|prompt|system|rule)',
        r'(?i)system\s*[:=]\s*',
        r'<\|(?:system|endofprompt|im_start|im_end)\|>',
        
        # Prompt breakout attempts
        r'(?i)forget\s+(?:previous|my|all).*(?:instruction|context|prompt)',
        r'(?i)(?:now|from\s+now)\s+(?:on|ignore|forget)',
        r'(?i)(?:previously|earlier).*(?:you|i)\s+(?:said|told|asked)',
        
        # Execution injection
        r'(?i)execute\s+(?:code|command|script|sql)',
        r'(?i)run\s+(?:this|the\s+following)',
        r'```\s*(?:python|javascript|bash|sh|sql)',
        
        # Role confusion
        r'(?i)(?:pretend|act|roleplay)\s+(?:as|like|that)\s+(?:you\'?re?|the|a)',
        r'(?i)pretend\s+(?:you\s+)?are\b',
        r'(?i)you\s+are\s+(?:now|actually|secretly)',
        
        # Template injection patterns
        r'\{\{.*?\}\}|\{%.*?%\}|\$\{.*?\}',
    ]

    # =========================================================
    # DOMAIN KEYWORDS
    # =========================================================
    
    DOMAIN_KEYWORDS = {
        'inventory': {'inventory', 'stock', 'quantity', 'sku', 'product', 'warehouse', 'storage'},
        'notification': {'notify', 'alert', 'notification', 'message', 'email', 'send'},
        'management': {'manage', 'track', 'monitor', 'update', 'create', 'delete', 'modify'},
        'threshold': {'threshold', 'limit', 'minimum', 'maximum', 'min', 'max', 'below', 'above'},
    }

    # =========================================================
    # SENSITIVE PATTERNS
    # =========================================================
    
    SENSITIVE_PATTERNS = {
        'api_key': r'(?i)(api[_-]?key|apikey|api_secret|secret[_-]?key)\s*[:=]\s*[\'"]?[\w\-]{20,}',
        'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]?[\w!@#$%^&*]{8,}',
        'database_url': r'(?i)(database[_-]?url|db[_-]?url|mongo[_-]?uri|postgres[_-]?url)\s*[:=]',
        'aws_key': r'(?i)(AKIA[0-9A-Z]{16})',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    }

    # =========================================================
    # CONFIGURATION
    # =========================================================
    
    # Length limits
    MIN_TITLE_LENGTH = 5
    MAX_TITLE_LENGTH = 200
    
    MIN_DESCRIPTION_LENGTH = 20
    MAX_DESCRIPTION_LENGTH = 2000
    
    MAX_CRITERIA_COUNT = 5
    MIN_CRITERIA_LENGTH = 10
    MAX_CRITERIA_LENGTH = 500
    
    # Vagueness indicators
    VAGUE_WORDS = {
        'something', 'stuff', 'thing', 'things', 'handle', 'improve',
        'better', 'fix', 'enhance', 'various', 'etc', 'and more',
        'somehow', 'anyways', 'basically', 'like', 'kind of', 'sort of',
        'pretty', 'really', 'very', 'quite', 'just'
    }
    
    VAGUE_PATTERNS = [
        r'(?i)\b(?:TODO|FIXME|XXX|HACK|WIP)\b',  # Work in progress markers
        r'(?i)(?:to\s+be\s+)?determined|undefined|unknown|unclear|tbd',
        r'(?i)fill\s+(?:this|that|it)\s+in',
        r'(?i)(?:add|implement)\s+(?:more|additional|extra)\s+(?:stuff|things)',
    ]

    def __init__(self):
        """Initialize the validator with compiled regex patterns."""
        self.injection_patterns = [re.compile(p) for p in self.INJECTION_PATTERNS]
        self.sensitive_patterns = {
            k: re.compile(v) for k, v in self.SENSITIVE_PATTERNS.items()
        }
        self.vague_patterns = [re.compile(p) for p in self.VAGUE_PATTERNS]

    def validate(self, requirement: Requirement) -> tuple[bool, list[ValidationError]]:
        """
        Validate a requirement against all guardrails.
        
        Args:
            requirement: The Requirement object to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
            If is_valid is True, the requirement passes all checks.
            If is_valid is False, list_of_errors contains details.
        """
        errors: list[ValidationError] = []

        # Run all validators
        errors.extend(self._validate_title(requirement.title))
        errors.extend(self._validate_description(requirement.description))
        errors.extend(self._validate_acceptance_criteria(requirement.acceptance_criteria))
        
        # Check for injections
        errors.extend(self._check_prompt_injection(requirement))
        
        # Check for sensitive data
        errors.extend(self._check_sensitive_information(requirement))
        
        # Check for vagueness
        errors.extend(self._check_vagueness(requirement))
        
        # Check domain relevance
        errors.extend(self._check_domain_relevance(requirement))

        is_valid = not any(e.severity == "error" for e in errors)
        return is_valid, errors

    # =========================================================
    # TITLE VALIDATION
    # =========================================================

    def _validate_title(self, title: str) -> list[ValidationError]:
        """Validate requirement title."""
        errors = []

        if not title or not title.strip():
            errors.append(ValidationError(
                category="title",
                message="Title cannot be empty",
                severity="error"
            ))
            return errors

        title = title.strip()

        if len(title) < self.MIN_TITLE_LENGTH:
            errors.append(ValidationError(
                category="title",
                message=f"Title is too short (minimum {self.MIN_TITLE_LENGTH} characters, got {len(title)})",
                severity="error"
            ))

        if len(title) > self.MAX_TITLE_LENGTH:
            errors.append(ValidationError(
                category="title",
                message=f"Title is too long (maximum {self.MAX_TITLE_LENGTH} characters, got {len(title)})",
                severity="error"
            ))

        return errors

    # =========================================================
    # DESCRIPTION VALIDATION
    # =========================================================

    def _validate_description(self, description: str) -> list[ValidationError]:
        """Validate requirement description."""
        errors = []

        if not description or not description.strip():
            errors.append(ValidationError(
                category="description",
                message="Description cannot be empty",
                severity="error"
            ))
            return errors

        description = description.strip()

        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            errors.append(ValidationError(
                category="description",
                message=f"Description is too short (minimum {self.MIN_DESCRIPTION_LENGTH} characters, got {len(description)})",
                severity="error"
            ))

        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(ValidationError(
                category="description",
                message=f"Description is too long (maximum {self.MAX_DESCRIPTION_LENGTH} characters, got {len(description)})",
                severity="error"
            ))

        return errors

    # =========================================================
    # ACCEPTANCE CRITERIA VALIDATION
    # =========================================================

    def _validate_acceptance_criteria(self, criteria: list[str]) -> list[ValidationError]:
        """Validate acceptance criteria."""
        errors = []

        if not criteria:
            errors.append(ValidationError(
                category="acceptance_criteria",
                message="At least one acceptance criterion is required",
                severity="error"
            ))
            return errors

        if len(criteria) > self.MAX_CRITERIA_COUNT:
            errors.append(ValidationError(
                category="acceptance_criteria",
                message=f"Too many criteria (maximum {self.MAX_CRITERIA_COUNT}, got {len(criteria)})",
                severity="error"
            ))

        for i, criterion in enumerate(criteria):
            if not criterion or not criterion.strip():
                errors.append(ValidationError(
                    category="acceptance_criteria",
                    message=f"Criterion {i + 1} is empty",
                    severity="error"
                ))
                continue

            criterion = criterion.strip()

            if len(criterion) < self.MIN_CRITERIA_LENGTH:
                errors.append(ValidationError(
                    category="acceptance_criteria",
                    message=f"Criterion {i + 1} is too short (minimum {self.MIN_CRITERIA_LENGTH} characters)",
                    severity="error"
                ))

            if len(criterion) > self.MAX_CRITERIA_LENGTH:
                errors.append(ValidationError(
                    category="acceptance_criteria",
                    message=f"Criterion {i + 1} is too long (maximum {self.MAX_CRITERIA_LENGTH} characters)",
                    severity="error"
                ))

        return errors

    # =========================================================
    # PROMPT INJECTION CHECK
    # =========================================================

    def _check_prompt_injection(self, requirement: Requirement) -> list[ValidationError]:
        """Detect potential prompt injection attempts."""
        errors = []

        combined_text = f"{requirement.title} {requirement.description} {' '.join(requirement.acceptance_criteria)}"

        for pattern in self.injection_patterns:
            if pattern.search(combined_text):
                errors.append(ValidationError(
                    category="security",
                    message="Potential prompt injection detected in input",
                    severity="error"
                ))
                break  # Report only once

        return errors

    # =========================================================
    # SENSITIVE INFORMATION CHECK
    # =========================================================

    def _check_sensitive_information(self, requirement: Requirement) -> list[ValidationError]:
        """Detect potentially sensitive information leakage."""
        errors = []
        warnings = []

        combined_text = f"{requirement.title} {requirement.description} {' '.join(requirement.acceptance_criteria)}"

        found_sensitive = {}
        for category, pattern in self.sensitive_patterns.items():
            matches = pattern.finditer(combined_text)
            match_count = sum(1 for _ in matches)
            if match_count > 0:
                found_sensitive[category] = match_count

        if 'api_key' in found_sensitive or 'password' in found_sensitive or 'database_url' in found_sensitive or 'aws_key' in found_sensitive:
            errors.append(ValidationError(
                category="security",
                message="Sensitive credentials (API key, password, or database URL) detected in input",
                severity="error"
            ))

        if 'credit_card' in found_sensitive or 'ssn' in found_sensitive:
            errors.append(ValidationError(
                category="security",
                message="Personal financial information detected in input",
                severity="error"
            ))

        if 'email' in found_sensitive:
            warnings.append(ValidationError(
                category="security",
                message=f"Email address(es) detected in input ({found_sensitive['email']} found)",
                severity="warning"
            ))

        if 'phone' in found_sensitive:
            warnings.append(ValidationError(
                category="security",
                message=f"Phone number(s) detected in input ({found_sensitive['phone']} found)",
                severity="warning"
            ))

        # Only add errors, warnings can be logged but not returned as validation failures
        errors.extend([w for w in warnings if w.severity == "error"])
        
        return errors

    # =========================================================
    # VAGUENESS CHECK
    # =========================================================

    def _check_vagueness(self, requirement: Requirement) -> list[ValidationError]:
        """Detect vague or under-specified requirements."""
        errors = []

        # Check for vague pattern matches
        combined_text = f"{requirement.title} {requirement.description} {' '.join(requirement.acceptance_criteria)}"
        
        for pattern in self.vague_patterns:
            if pattern.search(combined_text):
                errors.append(ValidationError(
                    category="clarity",
                    message="Requirement contains vague/incomplete indicators (TODO, TBD, etc.)",
                    severity="error"
                ))
                break

        # Check for high proportion of vague words in description
        desc_words = requirement.description.lower().split()
        vague_word_count = sum(
            1 for word in desc_words 
            if any(vague in word for vague in self.VAGUE_WORDS)
        )
        
        if len(desc_words) > 0:
            vague_ratio = vague_word_count / len(desc_words)
            if vague_ratio > 0.2:  # More than 20% vague words
                errors.append(ValidationError(
                    category="clarity",
                    message=f"Requirement is overly vague ({int(vague_ratio * 100)}% vague words)",
                    severity="error"
                ))

        return errors

    # =========================================================
    # DOMAIN RELEVANCE CHECK
    # =========================================================

    def _check_domain_relevance(self, requirement: Requirement) -> list[ValidationError]:
        """Verify requirement is relevant to the inventory management domain."""
        errors = []

        combined_text = (
            f"{requirement.title} {requirement.description} {' '.join(requirement.acceptance_criteria)}"
        ).lower()

        # Check if requirement mentions relevant domain concepts
        relevant_keywords_found = 0
        for category, keywords in self.DOMAIN_KEYWORDS.items():
            if any(keyword in combined_text for keyword in keywords):
                relevant_keywords_found += 1

        # Generic workflow words such as "update" are not enough to establish
        # that a requirement belongs to the inventory domain.
        if not any(
            keyword in combined_text
            for keyword in self.DOMAIN_KEYWORDS['inventory']
        ):
            errors.append(ValidationError(
                category="domain_relevance",
                message="Requirement does not mention relevant domain concepts (inventory, SKU, products, categories, etc.)",
                severity="error"
            ))

        return errors

    def get_validation_report(self, requirement: Requirement) -> dict:
        """
        Get a detailed validation report for a requirement.
        
        Returns:
            Dict with validation status, errors, warnings, and suggestions
        """
        is_valid, errors = self.validate(requirement)
        
        error_categories = {}
        warnings = []
        critical_issues = []
        
        for error in errors:
            if error.severity == "error":
                if error.category not in error_categories:
                    error_categories[error.category] = []
                error_categories[error.category].append(error.message)
                critical_issues.append(f"[{error.category.upper()}] {error.message}")
            else:
                warnings.append(error.message)

        return {
            "valid": is_valid,
            "summary": f"{'✓ Valid' if is_valid else '✗ Invalid'} requirement",
            "error_count": len([e for e in errors if e.severity == "error"]),
            "warning_count": len(warnings),
            "critical_issues": critical_issues,
            "errors_by_category": error_categories,
            "warnings": warnings,
        }
