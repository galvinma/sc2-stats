from pydantic import BaseModel, ConfigDict, AliasChoices, Field


class SeasonResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    season_id: int = Field(validation_alias=AliasChoices("seasonId"))
    number: int
    year: int
    start_date: str = Field(validation_alias=AliasChoices("startDate"))
    end_date: str = Field(validation_alias=AliasChoices("endDate"))
