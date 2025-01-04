from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.db.model import Profile


class Match(BaseModel):
    model_config = ConfigDict(strict=True)

    map: str
    type: str
    decision: str
    speed: str
    date: int


class MatchHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    profile: Optional[Profile] = None
    matches: Optional[List[Match]] = []
