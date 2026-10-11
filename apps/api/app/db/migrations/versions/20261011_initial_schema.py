"""Initial schema

Revision ID: 20261011_initial_schema
Revises: 
Create Date: 2026-10-11 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from app.db.models.models import (
    AttrsSource,
    BodySource,
    ConsentKind,
    MediaKind,
    MediaStatus,
    ModelKind,
    ModelStatus,
    OutfitEventType,
    OutfitPolicy,
    OutfitSlot,
)

# revision identifiers, used by Alembic.
revision = "20261011_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", UUID(as_uuid=True), nullable=True),
        sa.Column("ua_hash", sa.String(length=64), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "consents",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Enum(ConsentKind, name="consentkind"), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", name="uq_consent_user_kind"),
    )
    op.create_index(op.f("ix_consents_user_id"), "consents", ["user_id"], unique=False)

    op.create_table(
        "profiles",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("age_range", sa.String(length=20), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("preferred_categories", ARRAY(sa.String()), nullable=True),
        sa.Column("fav_colors", ARRAY(sa.String()), nullable=True),
        sa.Column("styles", ARRAY(sa.String()), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("occasions", ARRAY(sa.String()), nullable=True),
        sa.Column("region", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "body_profiles",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("measurements_enc", sa.LargeBinary(), nullable=True),
        sa.Column("shape", sa.String(length=50), nullable=True),
        sa.Column("shape_confidence", sa.Float(), nullable=True),
        sa.Column("ratios", JSONB(), nullable=True),
        sa.Column("source", sa.Enum(BodySource, name="bodysource"), nullable=True),
        sa.Column("user_corrected_shape", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Enum(MediaKind, name="mediakind"), nullable=False),
        sa.Column("bucket", sa.String(length=100), nullable=True),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("mime", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Enum(MediaStatus, name="mediastatus"), nullable=False, server_default=str(MediaStatus.PENDING)),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_assets_user_id"), "media_assets", ["user_id"], unique=False)

    op.create_table(
        "wardrobe_items",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=True),
        sa.Column("cutout_asset_id", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("colors", JSONB(), nullable=True),
        sa.Column("pattern", sa.String(length=50), nullable=True),
        sa.Column("material", sa.String(length=50), nullable=True),
        sa.Column("sleeve", sa.String(length=50), nullable=True),
        sa.Column("neckline", sa.String(length=50), nullable=True),
        sa.Column("fit", sa.String(length=50), nullable=True),
        sa.Column("length", sa.String(length=50), nullable=True),
        sa.Column("style_tags", ARRAY(sa.String()), nullable=True),
        sa.Column("occasions", ARRAY(sa.String()), nullable=True),
        sa.Column("seasons", ARRAY(sa.String()), nullable=True),
        sa.Column("formality", sa.Integer(), nullable=True),
        sa.Column("attrs_confidence", JSONB(), nullable=True),
        sa.Column("attrs_source", sa.Enum(AttrsSource, name="attrssource"), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("wear_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_worn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"]),
        sa.ForeignKeyConstraint(["cutout_asset_id"], ["media_assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wardrobe_items_category"), "wardrobe_items", ["category"], unique=False)
    op.create_index(op.f("ix_wardrobe_items_user_id"), "wardrobe_items", ["user_id"], unique=False)

    op.create_table(
        "item_label_corrections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(length=50), nullable=False),
        sa.Column("predicted", sa.String(length=200), nullable=True),
        sa.Column("corrected", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["wardrobe_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_label_corrections_item_id"), "item_label_corrections", ["item_id"], unique=False)

    op.create_table(
        "outfits",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("occasion", sa.String(length=100), nullable=True),
        sa.Column("context", JSONB(), nullable=True),
        sa.Column("score_rules", sa.Float(), nullable=True),
        sa.Column("score_model", sa.Float(), nullable=True),
        sa.Column("score_final", sa.Float(), nullable=True),
        sa.Column("ranker_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("policy", sa.Enum(OutfitPolicy, name="outfitpolicy"), nullable=True),
        sa.Column("propensity", sa.Float(), nullable=True),
        sa.Column("features", JSONB(), nullable=True),
        sa.Column("explanation", JSONB(), nullable=True),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outfits_user_id"), "outfits", ["user_id"], unique=False)

    op.create_table(
        "outfit_items",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("outfit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("slot", sa.Enum(OutfitSlot, name="outfitslot"), nullable=False),
        sa.Column("wardrobe_item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wardrobe_item_id"], ["wardrobe_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outfit_items_outfit_id"), "outfit_items", ["outfit_id"], unique=False)

    op.create_table(
        "outfit_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("outfit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum(OutfitEventType, name="outfiteventtype"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("policy", sa.Enum(OutfitPolicy, name="outfitpolicy"), nullable=True),
        sa.Column("propensity", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outfit_events_user_ts", "outfit_events", ["user_id", "ts"], unique=False)

    op.create_table(
        "user_style_state",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("style_dna", JSONB(), nullable=True),
        sa.Column("n_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "catalog_products",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("brand", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("colors", JSONB(), nullable=True),
        sa.Column("pattern", sa.String(length=50), nullable=True),
        sa.Column("fit", sa.String(length=50), nullable=True),
        sa.Column("style_tags", ARRAY(sa.String()), nullable=True),
        sa.Column("occasions", ARRAY(sa.String()), nullable=True),
        sa.Column("formality", sa.Integer(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("trend_tags", ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_catalog_source_ext_id"),
    )
    op.create_index(op.f("ix_catalog_products_category"), "catalog_products", ["category"], unique=False)

    op.create_table(
        "wishlist_items",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=True),
        sa.Column("outfit_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wishlist_items_user_id"), "wishlist_items", ["user_id"], unique=False)

    op.create_table(
        "trends",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", ARRAY(sa.String()), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Enum(ModelKind, name="modelkind"), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("artifact_key", sa.String(length=500), nullable=True),
        sa.Column("metrics", JSONB(), nullable=True),
        sa.Column("status", sa.Enum(ModelStatus, name="modelstatus"), nullable=False, server_default=str(ModelStatus.SHADOW)),
        sa.Column("n_train", sa.Integer(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("meta", JSONB(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_audit_log_user_id"), "audit_log", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_user_id"), table_name="audit_log")
    op.drop_table("model_versions")
    op.drop_table("trends")
    op.drop_table("wishlist_items")
    op.drop_index(op.f("ix_catalog_products_category"), table_name="catalog_products")
    op.drop_table("catalog_products")
    op.drop_table("user_style_state")
    op.drop_index("ix_outfit_events_user_ts", table_name="outfit_events")
    op.drop_table("outfit_events")
    op.drop_index(op.f("ix_outfit_items_outfit_id"), table_name="outfit_items")
    op.drop_table("outfit_items")
    op.drop_index(op.f("ix_outfits_user_id"), table_name="outfits")
    op.drop_table("outfits")
    op.drop_index(op.f("ix_item_label_corrections_item_id"), table_name="item_label_corrections")
    op.drop_table("item_label_corrections")
    op.drop_index(op.f("ix_wardrobe_items_user_id"), table_name="wardrobe_items")
    op.drop_index(op.f("ix_wardrobe_items_category"), table_name="wardrobe_items")
    op.drop_table("wardrobe_items")
    op.drop_index(op.f("ix_media_assets_user_id"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_table("body_profiles")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_consents_user_id"), table_name="consents")
    op.drop_table("consents")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
