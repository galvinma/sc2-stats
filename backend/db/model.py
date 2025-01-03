import uuid
from typing import List, Optional

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class League(Base):
    __tablename__ = "league"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    league_id: Mapped[int] = mapped_column()
    region_id: Mapped[int] = mapped_column()
    season_id: Mapped[int] = mapped_column()
    queue_id: Mapped[int] = mapped_column()
    team_type: Mapped[int] = mapped_column()

    ladders: Mapped[List["Ladder"]] = relationship(back_populates="league")

    UniqueConstraint(league_id, region_id, season_id, queue_id, team_type)

    def __repr__(self) -> str:
        return (
            f"League(id={self.id!r}, "
            + f"league_id={self.league_id!r}, "
            + f"region_id={self.region_id!r}, "
            + f"season_id={self.season_id!r}, "
            + f"queue_id={self.queue_id!r}, "
            + f"team_type={self.team_type!r})"
        )


class Ladder(Base):
    __tablename__ = "ladder"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    ladder_id: Mapped[int] = mapped_column()
    region_id: Mapped[int] = mapped_column()
    min_rating: Mapped[Optional[int]] = mapped_column()
    max_rating: Mapped[Optional[int]] = mapped_column()
    member_count: Mapped[Optional[int]] = mapped_column()

    league_id = mapped_column(ForeignKey("league.id"))
    league: Mapped[League] = relationship(back_populates="ladders")

    UniqueConstraint(league_id, ladder_id, region_id)

    def __repr__(self) -> str:
        return (
            f"Ladder(id={self.id!r}, "
            + f"ladder_id={self.ladder_id!r}, "
            + f"region_id={self.region_id!r}, "
            + f"min_rating={self.min_rating!r}, "
            + f"max_rating={self.max_rating!r}, "
            + f"member_count={self.member_count!r})"
        )


class Character(Base):
    __tablename__ = "character"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    character_id: Mapped[str] = mapped_column()
    realm: Mapped[int] = mapped_column()
    region: Mapped[int] = mapped_column()
    display_name: Mapped[str] = mapped_column()
    clan_name: Mapped[Optional[str]] = mapped_column()
    clan_tag: Mapped[Optional[str]] = mapped_column()
    profile_path: Mapped[str] = mapped_column()
    join_timestamp: Mapped[int] = mapped_column()
    points: Mapped[Optional[int]] = mapped_column()
    wins: Mapped[Optional[int]] = mapped_column()
    losses: Mapped[Optional[int]] = mapped_column()
    highest_rank: Mapped[Optional[int]] = mapped_column()
    previous_rank: Mapped[Optional[int]] = mapped_column()
    favorite_race_p1: Mapped[Optional[str]] = mapped_column()

    UniqueConstraint(character_id, realm, region)

    def __repr__(self) -> str:
        return (
            f"Character(id={self.id!r}, "
            + f"character_id={self.character_id!r}, "
            + f"realm={self.realm!r}, "
            + f"region={self.region!r}, "
            + f"display_name={self.display_name!r}, "
            + f"clan_name={self.clan_name!r}, "
            + f"clan_tag={self.clan_tag!r}, "
            + f"profile_path={self.profile_path!r}, "
            + f"join_timestamp={self.join_timestamp!r}, "
            + f"points={self.points!r}, "
            + f"wins={self.wins!r}, "
            + f"losses={self.losses!r}, "
            + f"highest_rank={self.highest_rank!r}, "
            + f"previous_rank={self.previous_rank!r}, "
            + f"favorite_race_p1={self.favorite_race_p1!r})"
        )
