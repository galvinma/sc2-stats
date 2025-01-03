"""Add character table

Revision ID: 5e058b1563a9
Revises: 7ba72e14cbbc
Create Date: 2025-01-03 18:47:57.267788

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e058b1563a9"
down_revision: Union[str, None] = "7ba72e14cbbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "character",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.String(), nullable=False),
        sa.Column("realm", sa.Integer(), nullable=False),
        sa.Column("region", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("clan_name", sa.String(), nullable=True),
        sa.Column("clan_tag", sa.String(), nullable=True),
        sa.Column("profile_path", sa.String(), nullable=False),
        sa.Column("join_timestamp", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("highest_rank", sa.Integer(), nullable=True),
        sa.Column("previous_rank", sa.Integer(), nullable=True),
        sa.Column("favorite_race_p1", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id", "realm", "region"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("character")
    # ### end Alembic commands ###
