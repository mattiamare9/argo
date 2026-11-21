"""audit events (append-only)

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=200), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure')", name=op.f("ck_audit_events_outcome")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_occurred_at"), "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_target", "audit_events", ["target_type", "target_id"])

    # Append-only a livello DB: nessun codice applicativo può modificare o cancellare eventi.
    # Il proprietario della tabella può comunque disabilitare il trigger: in produzione l'app
    # userà un ruolo DB non proprietario (Fase 7, vedi SECURITY.md).
    op.execute(
        """
        CREATE FUNCTION audit_events_block_changes() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events è append-only (% non consentito)', TG_OP;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_block_changes();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION audit_events_block_changes();
        """
    )


def downgrade() -> None:
    op.drop_table("audit_events")  # rimuove anche i trigger
    op.execute("DROP FUNCTION audit_events_block_changes()")
