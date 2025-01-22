"""
Pydantic schema for profile APIs
"""

from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from backend.db.model import LadderMember
from backend.enums import Race


class TeamMember(BaseModel):
    model_config = ConfigDict(strict=True)

    profile_id: str = Field(validation_alias=AliasChoices("id"))
    realm_id: int = Field(validation_alias=AliasChoices("realm"))
    region_id: int = Field(validation_alias=AliasChoices("region"))
    display_name: str = Field(validation_alias=AliasChoices("displayName"))
    race: Race = Field(default=None, validation_alias=AliasChoices("favoriteRace"))

    @field_validator("race", mode="before")
    @classmethod
    def convert(cls, value: str) -> Race:
        return Race(value.strip().upper())


class LadderTeam(BaseModel):
    model_config = ConfigDict(strict=True, use_enum_values=True)

    team_members: Optional[List[TeamMember]] = Field(default=[], validation_alias=AliasChoices("teamMembers"))
    previous_rank: Optional[int] = Field(default=None, validation_alias=AliasChoices("previousRank"))
    points: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    mmr: Optional[int] = None
    join_timestamp: int = Field(validation_alias=AliasChoices("joinTimestamp"))


class ProfileLadderResponse(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    ladder_member: Optional[LadderMember] = None
    ladder_teams: Optional[List[LadderTeam]] = Field(default=[], validation_alias=AliasChoices("ladderTeams"))
