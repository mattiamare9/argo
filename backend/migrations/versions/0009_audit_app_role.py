"""audit: il ruolo applicativo può solo inserire e leggere

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Il ruolo esiste solo in produzione (deploy/postgres/prod-init.sh): in sviluppo è un no-op.
REVOKE = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argo_app') THEN
        REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM argo_app;
    END IF;
END $$;
"""

GRANT_BACK = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argo_app') THEN
        GRANT UPDATE, DELETE ON audit_events TO argo_app;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(REVOKE)


def downgrade() -> None:
    op.execute(GRANT_BACK)
