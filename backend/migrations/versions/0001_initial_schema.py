"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-29 01:46:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # regulations
    op.create_table(
        "regulations",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("authority", sa.String(200)),
        sa.Column("scope", sa.Text()),
        sa.Column("ml_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("ml_model_version", sa.String(20)),
        sa.Column("positive_label_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("negative_label_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_model_trained", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # substances
    op.create_table(
        "substances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("cas_number", sa.String(50), unique=True),
        sa.Column("ec_number", sa.String(50)),
        sa.Column("smiles", sa.String(1000)),
        sa.Column("change_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # substance_regulation_status
    op.create_table(
        "substance_regulation_status",
        sa.Column("substance_id", sa.Integer(), sa.ForeignKey("substances.id"), primary_key=True),
        sa.Column("regulation_id", sa.String(50), sa.ForeignKey("regulations.id"), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("effective_date", sa.Date()),
    )

    # substance_properties
    op.create_table(
        "substance_properties",
        sa.Column("substance_id", sa.Integer(), sa.ForeignKey("substances.id"), primary_key=True),
        sa.Column("molecular_weight", sa.Float()),
        sa.Column("logp", sa.Float()),
        sa.Column("hbd", sa.Integer()),
        sa.Column("hba", sa.Integer()),
        sa.Column("tpsa", sa.Float()),
        sa.Column("rotatable_bonds", sa.Integer()),
        sa.Column("aromatic_rings", sa.Integer()),
        sa.Column("heavy_atoms", sa.Integer()),
        sa.Column("bcf", sa.Float()),
        sa.Column("half_life_soil", sa.Float()),
        sa.Column("lc50_fish", sa.Float()),
        sa.Column("carcinogenicity_flag", sa.Boolean()),
        sa.Column("morgan_fp_pca_50", postgresql.ARRAY(sa.Float())),
        sa.Column("has_smiles", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("has_epa_data", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # regulatory_changes
    op.create_table(
        "regulatory_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("substance_id", sa.Integer(), sa.ForeignKey("substances.id")),
        sa.Column("regulation_id", sa.String(50), sa.ForeignKey("regulations.id")),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("old_hash", sa.String(64)),
        sa.Column("new_hash", sa.String(64)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false")),
    )

    # boms
    op.create_table(
        "boms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_type", sa.String(50), server_default=sa.text("'upload'")),
        sa.Column("file_format", sa.String(20)),
        sa.Column("total_parts", sa.Integer(), server_default=sa.text("0")),
        sa.Column("compliance_status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # bom_parts
    op.create_table(
        "bom_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bom_id", sa.Integer(), sa.ForeignKey("boms.id", ondelete="CASCADE")),
        sa.Column("line_number", sa.Integer()),
        sa.Column("part_number", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("manufacturer", sa.String(200)),
        sa.Column("supplier", sa.String(200)),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1")),
        sa.Column("unit", sa.String(20), server_default=sa.text("'pcs'")),
        sa.Column("cas_numbers", sa.String(500)),
        sa.Column("parent_part_id", sa.Integer(), sa.ForeignKey("bom_parts.id")),
        sa.Column("level", sa.Integer(), server_default=sa.text("0")),
        sa.Column("scan_status", sa.String(20), server_default=sa.text("'pending'")),
    )

    # scan_results
    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bom_id", sa.Integer(), sa.ForeignKey("boms.id")),
        sa.Column("part_id", sa.Integer(), sa.ForeignKey("bom_parts.id")),
        sa.Column("regulation_id", sa.String(50), sa.ForeignKey("regulations.id")),
        sa.Column("cas_number", sa.String(50)),
        sa.Column("hit_type", sa.String(50)),
        sa.Column("risk_score", sa.Float()),
        sa.Column("severity", sa.String(20)),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # regulatory_summaries
    op.create_table(
        "regulatory_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("substance_id", sa.Integer(), sa.ForeignKey("substances.id")),
        sa.Column("regulation_id", sa.String(50), sa.ForeignKey("regulations.id")),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text()),  # Will be altered to vector after extension is ready
        sa.Column("model_used", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ml_model_performance
    op.create_table(
        "ml_model_performance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("regulation_id", sa.String(50), sa.ForeignKey("regulations.id")),
        sa.Column("model_version", sa.String(20)),
        sa.Column("mlflow_run_id", sa.String(50)),
        sa.Column("trained_at", sa.DateTime(timezone=True)),
        sa.Column("roc_auc", sa.Float()),
        sa.Column("average_precision", sa.Float()),
        sa.Column("precision_at_100", sa.Float()),
        sa.Column("brier_score", sa.Float()),
        sa.Column("n_train_positive", sa.Integer()),
        sa.Column("n_train_negative", sa.Integer()),
        sa.Column("n_test_positive", sa.Integer()),
        sa.Column("n_test_negative", sa.Integer()),
        sa.Column("holdout_cutoff_date", sa.Date()),
        sa.Column("promoted_to_production", sa.Boolean(), server_default=sa.text("false")),
    )

    # compliance_overrides
    op.create_table(
        "compliance_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("condition_supplier", sa.String(200)),
        sa.Column("condition_cas", sa.String(50)),
        sa.Column("condition_regulation", sa.String(50)),
        sa.Column("action", sa.String(50)),
        sa.Column("reason", sa.Text()),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Seed regulations
    op.execute("""
        INSERT INTO regulations (id, name, authority, scope, ml_enabled) VALUES
        ('eu_reach_svhc', 'EU REACH SVHC Candidate List', 'ECHA', 'Substances of Very High Concern in the EU', TRUE),
        ('us_state_pfas', 'US State PFAS Restrictions', 'Multi-state', 'Per- and polyfluoroalkyl substances restrictions across US states', TRUE),
        ('eu_rohs', 'EU RoHS Directive 2011/65/EU', 'European Commission', 'Restriction of Hazardous Substances in electrical and electronic equipment', FALSE),
        ('us_tsca_6h', 'US TSCA Section 6(h) PBT', 'US EPA', 'Persistent Bioaccumulative and Toxic chemicals under TSCA', FALSE),
        ('cn_rohs', 'China RoHS 2 (SJ/T 11363)', 'MIIT China', 'Restriction of Hazardous Substances in China', FALSE)
    """)

    # Alter embedding column to vector type and create index
    op.execute("ALTER TABLE regulatory_summaries ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768)")
    op.execute("CREATE INDEX ON regulatory_summaries USING ivfflat (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.drop_index("regulatory_summaries_embedding_idx", table_name="regulatory_summaries")
    op.drop_table("compliance_overrides")
    op.drop_table("ml_model_performance")
    op.drop_table("regulatory_summaries")
    op.drop_table("scan_results")
    op.drop_table("bom_parts")
    op.drop_table("boms")
    op.drop_table("regulatory_changes")
    op.drop_table("substance_properties")
    op.drop_table("substance_regulation_status")
    op.drop_table("substances")
    op.drop_table("regulations")
    op.execute("DROP EXTENSION IF EXISTS vector")
