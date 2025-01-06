"""
Pydantic schema for legacy APIs
"""

from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from backend.db.model import Ladder, Profile
from backend.enums import Race


class LadderCharacter(BaseModel):
    model_config = ConfigDict(strict=True)

    profile_id: str = Field(validation_alias=AliasChoices("id"))
    realm_id: int = Field(validation_alias=AliasChoices("realm"))
    region_id: int = Field(validation_alias=AliasChoices("region"))
    display_name: str = Field(validation_alias=AliasChoices("displayName"))
    clan_name: str = Field(validation_alias=AliasChoices("clanName"))
    clan_tag: str = Field(validation_alias=AliasChoices("clanTag"))
    profile_path: str = Field(validation_alias=AliasChoices("profilePath"))


class LadderMember(BaseModel):
    model_config = ConfigDict(strict=True, use_enum_values=True)

    character: LadderCharacter
    join_timestamp: int = Field(validation_alias=AliasChoices("joinTimestamp"))
    points: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    highest_rank: Optional[int] = Field(default=None, validation_alias=AliasChoices("highestRank"))
    previous_rank: Optional[int] = Field(default=None, validation_alias=AliasChoices("previousRank"))
    race: Optional[Race] = Field(default=None, validation_alias=AliasChoices("favoriteRaceP1"))

    @field_validator("race", mode="before")
    @classmethod
    def convert(cls, value: str) -> Race:
        return Race(value.strip().upper())


class LegacyLadderResponse(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    ladder: Optional[Ladder] = None
    ladder_members: Optional[List[LadderMember]] = Field(default=[], validation_alias=AliasChoices("ladderMembers"))


class Match(BaseModel):
    model_config = ConfigDict(strict=True)

    map: str
    type: str
    decision: str
    speed: str
    date: int


class LegacyMatchHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    profile: Optional[Profile] = None
    matches: Optional[List[Match]] = []
