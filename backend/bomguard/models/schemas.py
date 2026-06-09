"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RegulationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    authority: str | None = None
    scope: str | None = None
    ml_enabled: bool = False
    ml_model_version: str | None = None
    positive_label_count: int = 0
    negative_label_count: int = 0


class SubstanceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cas_number: str | None = None
    ec_number: str | None = None
    smiles: str | None = None


class BomPartSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_number: int | None = None
    part_number: str
    description: str | None = None
    manufacturer: str | None = None
    supplier: str | None = None
    quantity: int = 1
    unit: str = "pcs"
    cas_numbers: str | None = None


class BomSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    source_type: str = "upload"
    file_format: str | None = None
    total_parts: int = 0
    compliance_status: str = "pending"
    user_id: str | None = None
    created_at: datetime | None = None
    hit_count: int = 0


class BomDetailSchema(BomSchema):
    parts: list[BomPartSchema] = []


class ScanResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bom_id: int | None = None
    part_id: int | None = None
    regulation_id: str | None = None
    cas_number: str | None = None
    hit_type: str | None = None
    risk_score: float | None = None
    severity: str | None = None
    details: dict[str, Any] | None = None


class ScanResultDetailSchema(ScanResultSchema):
    """Scan result enriched with part metadata."""

    part_number: str | None = None
    part_description: str | None = None


class BomUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    user_id: str | None = None


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None


class UserPreferenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    subscribed_regulation_ids: list[str] = []
    default_regulation_ids: list[str] = []
    email_notifications: bool = True


class ShapFeatureContribution(BaseModel):
    feature: str
    value: float
    contribution: float


class ShapExplanationResponse(BaseModel):
    cas: str
    regulation: str
    predicted_risk: float
    base_value: float
    top_features: list[ShapFeatureContribution]


class HealthCheckResponse(BaseModel):
    status: str
