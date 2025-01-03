from typing import List, Optional
from pydantic import ConfigDict, Field, BaseModel


class LeagueKey(BaseModel):
    model_config = ConfigDict(strict=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int
    season_id: int
    queue_id: int
    team_type: int


class LeagueDivision(BaseModel):
    model_config = ConfigDict(strict=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    ladder_id: int
    member_count: int


class LeagueTier(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int
    min_rating: Optional[int] = None
    max_rating: Optional[int] = None
    division: Optional[List[LeagueDivision]] = []


class LeagueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    key: Optional[LeagueKey] = None
    tier: Optional[List[LeagueTier]] = []