from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class Match(BaseModel):
    model_config = ConfigDict(strict=True)

    map: str
    type: str
    decision: str
    speed: str
    date: int


class MatchHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    character_id: Optional[str] = None
    profile_id: Optional[str] = None
    realm_id: Optional[int] = None
    region_id: Optional[int] = None
    matches: Optional[List[Match]] = []
