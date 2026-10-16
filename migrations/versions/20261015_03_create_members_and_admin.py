"""US03: administradores e cadastro de membros do clube."""

import sqlalchemy as sa
from alembic import op

revision = "20261015_03"
down_revision = "20261015_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_table(
        "members",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("status", sa.String(8), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("email", name="uq_members_email"),
        sa.CheckConstraint("email = lower(btrim(email))", name="ck_members_email_normalized"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_members_status"),
    )


def downgrade() -> None:
    op.drop_table("members")
    op.drop_column("users", "is_admin")
