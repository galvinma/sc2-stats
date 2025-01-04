from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(strict=True)

    character: LadderCharacter
    join_timestamp: int = Field(validation_alias=AliasChoices("joinTimestamp"))
    points: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    highest_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    favorite_race_p1: Optional[str] = Field(default=None, validation_alias=AliasChoices("favoriteRaceP1"))


class LadderResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    ladder_members: Optional[List[LadderMember]] = Field(default=[], validation_alias=AliasChoices("ladderMembers"))
