"""Update unique constraints

Revision ID: 1f2d2b6aec13
Revises: 5a95766c17f7
Create Date: 2025-01-07 13:24:17.197662

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f2d2b6aec13"
down_revision: Union[str, None] = "5a95766c17f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("character_profile_id_display_name_key", "character", type_="unique")
    op.create_unique_constraint("character_unique_constraint", "character", ["profile_id", "display_name"])
    op.drop_constraint("character_mmr_character_id_race_mmr_date_key", "character_mmr", type_="unique")
    op.create_unique_constraint(
        "character_mmr_unique_constraint", "character_mmr", ["character_id", "race", "mmr", "date"]
    )
    op.drop_constraint("ladder_league_id_ladder_id_region_id_key", "ladder", type_="unique")
    op.create_unique_constraint("ladder_unique_constraint", "ladder", ["league_id", "ladder_id", "region_id"])
    op.drop_constraint("ladder_member_profile_id_ladder_id_join_timestamp_key", "ladder_member", type_="unique")
    op.create_unique_constraint(
        "ladder_member_unique_constraint", "ladder_member", ["profile_id", "ladder_id", "join_timestamp"]
    )
    op.drop_constraint("league_league_id_region_id_season_id_queue_id_team_type_key", "league", type_="unique")
    op.create_unique_constraint(
        "league_unique_constraint", "league", ["league_id", "region_id", "season_id", "queue_id", "team_type"]
    )
    op.drop_constraint("match_profile_id_date_key", "match", type_="unique")
    op.create_unique_constraint("match_unique_constraint", "match", ["profile_id", "date"])
    op.drop_constraint("profile_profile_id_realm_id_region_id_key", "profile", type_="unique")
    op.create_unique_constraint("profile_unique_constraint", "profile", ["profile_id", "realm_id", "region_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("profile_unique_constraint", "profile", type_="unique")
    op.create_unique_constraint(
        "profile_profile_id_realm_id_region_id_key", "profile", ["profile_id", "realm_id", "region_id"]
    )
    op.drop_constraint("match_unique_constraint", "match", type_="unique")
    op.create_unique_constraint("match_profile_id_date_key", "match", ["profile_id", "date"])
    op.drop_constraint("league_unique_constraint", "league", type_="unique")
    op.create_unique_constraint(
        "league_league_id_region_id_season_id_queue_id_team_type_key",
        "league",
        ["league_id", "region_id", "season_id", "queue_id", "team_type"],
    )
    op.drop_constraint("ladder_member_unique_constraint", "ladder_member", type_="unique")
    op.create_unique_constraint(
        "ladder_member_profile_id_ladder_id_join_timestamp_key",
        "ladder_member",
        ["profile_id", "ladder_id", "join_timestamp"],
    )
    op.drop_constraint("ladder_unique_constraint", "ladder", type_="unique")
    op.create_unique_constraint(
        "ladder_league_id_ladder_id_region_id_key", "ladder", ["league_id", "ladder_id", "region_id"]
    )
    op.drop_constraint("character_mmr_unique_constraint", "character_mmr", type_="unique")
    op.create_unique_constraint(
        "character_mmr_character_id_race_mmr_date_key", "character_mmr", ["character_id", "race", "mmr", "date"]
    )
    op.drop_constraint("character_unique_constraint", "character", type_="unique")
    op.create_unique_constraint("character_profile_id_display_name_key", "character", ["profile_id", "display_name"])
    # ### end Alembic commands ###
