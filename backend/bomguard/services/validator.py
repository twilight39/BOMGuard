"""Declaration rule-based validator."""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    severity: str
    rule_id: str
    message: str
    field: str
    suggestion: str


class DeclarationValidator:
    """Validates material declarations against regulatory substance lists."""

    def __init__(self, db: object) -> None:
        self.db = db

    def validate(self, declaration: object) -> list[ValidationResult]:
        """Validate a material declaration."""
        return []
