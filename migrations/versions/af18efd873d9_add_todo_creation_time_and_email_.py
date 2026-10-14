"""add todo creation time and email verification

Revision ID: af18efd873d9
Revises: 2d80d219e0b9
Create Date: 2026-10-14 09:09:27.984715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af18efd873d9'
down_revision: Union[str, Sequence[str], None] = '2d80d219e0b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "todos",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Remove the old integer default before changing the column type.
    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.Integer(),
        server_default=None,
    )

    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="priority::text",
    )

    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.String(),
        server_default=sa.text("'normal'"),
    )

    op.create_check_constraint(
        "check_todo_priority",
        "todos",
        "priority IN ('urgent', 'important', 'normal')",
    )

    # Preserve existing accounts as verified.
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )

    # New accounts must be unverified by default.
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
    )


def downgrade() -> None:
    op.drop_column("users", "is_verified")

    op.drop_constraint(
        "check_todo_priority",
        "todos",
        type_="check",
    )

    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.String(),
        server_default=None,
    )

    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.String(),
        type_=sa.Integer(),
        postgresql_using=(
            "CASE priority "
            "WHEN 'urgent' THEN 2 "
            "WHEN 'important' THEN 1 "
            "WHEN 'normal' THEN 0 "
            "ELSE 0 END"
        ),
    )

    op.alter_column(
        "todos",
        "priority",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
    )

    op.drop_column("todos", "created_at")
