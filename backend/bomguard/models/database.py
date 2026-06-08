"""SQLAlchemy models for the BOMGuard database schema."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Substance(Base):
    __tablename__ = "substances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    ec_number: Mapped[str | None] = mapped_column(String(50))
    smiles: Mapped[str | None] = mapped_column(String(1000))
    change_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    properties: Mapped["SubstanceProperties | None"] = relationship(
        "SubstanceProperties", back_populates="substance", uselist=False
    )
    regulation_statuses: Mapped[list["SubstanceRegulationStatus"]] = relationship(
        "SubstanceRegulationStatus", back_populates="substance"
    )
    regulatory_changes: Mapped[list["RegulatoryChange"]] = relationship(
        "RegulatoryChange", back_populates="substance"
    )
    summaries: Mapped[list["RegulatorySummary"]] = relationship(
        "RegulatorySummary", back_populates="substance"
    )


class Regulation(Base):
    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    authority: Mapped[str | None] = mapped_column(String(200))
    scope: Mapped[str | None] = mapped_column(Text)
    ml_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ml_model_version: Mapped[str | None] = mapped_column(String(20))
    positive_label_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_label_count: Mapped[int] = mapped_column(Integer, default=0)
    last_model_trained: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    regulation_statuses: Mapped[list["SubstanceRegulationStatus"]] = relationship(
        "SubstanceRegulationStatus", back_populates="regulation"
    )
    regulatory_changes: Mapped[list["RegulatoryChange"]] = relationship(
        "RegulatoryChange", back_populates="regulation"
    )
    summaries: Mapped[list["RegulatorySummary"]] = relationship(
        "RegulatorySummary", back_populates="regulation"
    )
    ml_performances: Mapped[list["MLModelPerformance"]] = relationship(
        "MLModelPerformance", back_populates="regulation"
    )


class SubstanceRegulationStatus(Base):
    __tablename__ = "substance_regulation_status"

    substance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("substances.id"), primary_key=True
    )
    regulation_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("regulations.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[Date | None] = mapped_column(Date)

    substance: Mapped["Substance"] = relationship("Substance", back_populates="regulation_statuses")
    regulation: Mapped["Regulation"] = relationship(
        "Regulation", back_populates="regulation_statuses"
    )


class SubstanceProperties(Base):
    __tablename__ = "substance_properties"

    substance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("substances.id"), primary_key=True
    )
    molecular_weight: Mapped[float | None] = mapped_column(Float)
    logp: Mapped[float | None] = mapped_column(Float)
    hbd: Mapped[int | None] = mapped_column(Integer)
    hba: Mapped[int | None] = mapped_column(Integer)
    tpsa: Mapped[float | None] = mapped_column(Float)
    rotatable_bonds: Mapped[int | None] = mapped_column(Integer)
    aromatic_rings: Mapped[int | None] = mapped_column(Integer)
    heavy_atoms: Mapped[int | None] = mapped_column(Integer)
    bcf: Mapped[float | None] = mapped_column(Float)
    half_life_soil: Mapped[float | None] = mapped_column(Float)
    lc50_fish: Mapped[float | None] = mapped_column(Float)
    carcinogenicity_flag: Mapped[bool | None] = mapped_column(Boolean)
    morgan_fp_pca_50: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    has_smiles: Mapped[bool] = mapped_column(Boolean, default=False)
    has_epa_data: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    substance: Mapped["Substance"] = relationship("Substance", back_populates="properties")


class RegulatoryChange(Base):
    __tablename__ = "regulatory_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    substance_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("substances.id"))
    regulation_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("regulations.id"))
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    old_hash: Mapped[str | None] = mapped_column(String(64))
    new_hash: Mapped[str | None] = mapped_column(String(64))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    substance: Mapped["Substance | None"] = relationship(
        "Substance", back_populates="regulatory_changes"
    )
    regulation: Mapped["Regulation | None"] = relationship(
        "Regulation", back_populates="regulatory_changes"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    boms: Mapped[list["Bom"]] = relationship("Bom", back_populates="user")
    preferences: Mapped["UserPreference | None"] = relationship(
        "UserPreference", back_populates="user", uselist=False
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), primary_key=True)
    subscribed_regulation_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    default_regulation_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class Bom(Base):
    __tablename__ = "boms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), default="upload")
    file_format: Mapped[str | None] = mapped_column(String(20))
    total_parts: Mapped[int] = mapped_column(Integer, default=0)
    compliance_status: Mapped[str] = mapped_column(String(20), default="pending")
    user_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User | None"] = relationship("User", back_populates="boms")
    parts: Mapped[list["BomPart"]] = relationship("BomPart", back_populates="bom")
    scan_results: Mapped[list["ScanResult"]] = relationship("ScanResult", back_populates="bom")


class BomPart(Base):
    __tablename__ = "bom_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bom_id: Mapped[int] = mapped_column(Integer, ForeignKey("boms.id", ondelete="CASCADE"))
    line_number: Mapped[int | None] = mapped_column(Integer)
    part_number: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    supplier: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    cas_numbers: Mapped[str | None] = mapped_column(String(500))
    parent_part_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bom_parts.id"))
    level: Mapped[int] = mapped_column(Integer, default=0)
    scan_status: Mapped[str] = mapped_column(String(20), default="pending")

    bom: Mapped["Bom"] = relationship("Bom", back_populates="parts")
    scan_results: Mapped[list["ScanResult"]] = relationship("ScanResult", back_populates="part")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bom_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("boms.id"))
    part_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bom_parts.id"))
    regulation_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("regulations.id"))
    cas_number: Mapped[str | None] = mapped_column(String(50))
    hit_type: Mapped[str | None] = mapped_column(String(50))
    risk_score: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str | None] = mapped_column(String(20))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bom: Mapped["Bom | None"] = relationship("Bom", back_populates="scan_results")
    part: Mapped["BomPart | None"] = relationship("BomPart", back_populates="scan_results")
    regulation: Mapped["Regulation | None"] = relationship("Regulation")


class RegulatorySummary(Base):
    __tablename__ = "regulatory_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    substance_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("substances.id"))
    regulation_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("regulations.id"))
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    model_used: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    substance: Mapped["Substance | None"] = relationship("Substance", back_populates="summaries")
    regulation: Mapped["Regulation | None"] = relationship(
        "Regulation", back_populates="summaries"
    )



class MLModelPerformance(Base):
    __tablename__ = "ml_model_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regulation_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("regulations.id"))
    model_version: Mapped[str | None] = mapped_column(String(20))
    mlflow_run_id: Mapped[str | None] = mapped_column(String(50))
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roc_auc: Mapped[float | None] = mapped_column(Float)
    average_precision: Mapped[float | None] = mapped_column(Float)
    precision_at_100: Mapped[float | None] = mapped_column(Float)
    brier_score: Mapped[float | None] = mapped_column(Float)
    n_train_positive: Mapped[int | None] = mapped_column(Integer)
    n_train_negative: Mapped[int | None] = mapped_column(Integer)
    n_test_positive: Mapped[int | None] = mapped_column(Integer)
    n_test_negative: Mapped[int | None] = mapped_column(Integer)
    holdout_cutoff_date: Mapped[Date | None] = mapped_column(Date)
    promoted_to_production: Mapped[bool] = mapped_column(Boolean, default=False)

    regulation: Mapped["Regulation | None"] = relationship(
        "Regulation", back_populates="ml_performances"
    )


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="thread", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")


class ComplianceOverride(Base):
    __tablename__ = "compliance_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    condition_supplier: Mapped[str | None] = mapped_column(String(200))
    condition_cas: Mapped[str | None] = mapped_column(String(50))
    condition_regulation: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
