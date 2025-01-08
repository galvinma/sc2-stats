import uuid
from typing import List, Optional

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.enums import Race
from backend.static import (
    CHARACTER_MMR_UNIQUE_CONSTRAINT,
    CHARACTER_UNIQUE_CONSTRAINT,
    LADDER_MEMBER_UNIQUE_CONSTRAINT,
    LADDER_UNIQUE_CONSTRAINT,
    LEAGUE_UNIQUE_CONSTRAINT,
    MATCH_UNIQUE_CONSTRAINT,
    PROFILE_UNIQUE_CONSTRAINT,
)


class Base(DeclarativeBase):
    pass

    def as_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}


class League(Base):
    __tablename__ = "league"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    league_id: Mapped[int] = mapped_column()
    region_id: Mapped[int] = mapped_column()
    season_id: Mapped[int] = mapped_column()
    queue_id: Mapped[int] = mapped_column()
    team_type: Mapped[int] = mapped_column()

    ladders: Mapped[List["Ladder"]] = relationship(back_populates="league")

    UniqueConstraint(league_id, region_id, season_id, queue_id, team_type, name=LEAGUE_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"League(id={self.id!r}, "
            + f"league_id={self.league_id!r}, "
            + f"region_id={self.region_id!r}, "
            + f"season_id={self.season_id!r}, "
            + f"queue_id={self.queue_id!r}, "
            + f"team_type={self.team_type!r}"
            + ")"
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
    ladder_members: Mapped[List["LadderMember"]] = relationship(back_populates="ladder")

    UniqueConstraint(league_id, ladder_id, region_id, name=LADDER_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"Ladder(id={self.id!r}, "
            + f"ladder_id={self.ladder_id!r}, "
            + f"region_id={self.region_id!r}, "
            + f"min_rating={self.min_rating!r}, "
            + f"max_rating={self.max_rating!r}, "
            + f"member_count={self.member_count!r}"
            + ")"
        )


class LadderMember(Base):
    __tablename__ = "ladder_member"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    join_timestamp: Mapped[int] = mapped_column()
    points: Mapped[Optional[int]] = mapped_column()
    wins: Mapped[Optional[int]] = mapped_column()
    losses: Mapped[Optional[int]] = mapped_column()
    highest_rank: Mapped[Optional[int]] = mapped_column()
    previous_rank: Mapped[Optional[int]] = mapped_column()
    race: Mapped[Optional[Race]] = mapped_column()

    profile_id = mapped_column(ForeignKey("profile.id"))
    profile: Mapped["Profile"] = relationship(back_populates="ladder_members")
    ladder_id = mapped_column(ForeignKey("ladder.id"))
    ladder: Mapped["Ladder"] = relationship(back_populates="ladder_members")

    UniqueConstraint(profile_id, ladder_id, join_timestamp, name=LADDER_MEMBER_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"LadderMember(id={self.id!r}, "
            + f"profile_id={self.profile_id!r}, "
            + f"ladder_id={self.ladder_id!r}, "
            + f"join_timestamp={self.join_timestamp!r}, "
            + f"points={self.points!r}, "
            + f"wins={self.wins!r}, "
            + f"losses={self.losses!r}, "
            + f"highest_rank={self.highest_rank!r}, "
            + f"previous_rank={self.previous_rank!r}, "
            + f"race={self.race!r}"
            + ")"
        )


class CharacterMMR(Base):
    __tablename__ = "character_mmr"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    race: Mapped[Race] = mapped_column()
    mmr: Mapped[int] = mapped_column()
    date: Mapped[int] = mapped_column()

    character_id = mapped_column(ForeignKey("character.id"))
    character: Mapped["Character"] = relationship(back_populates="character_mmrs")

    UniqueConstraint(character_id, race, mmr, date, name=CHARACTER_MMR_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"CharacterMMR(id={self.id!r}, "
            + f"character_id={self.character_id!r}, "
            + f"race={self.race!r}, "
            + f"mmr={self.mmr!r}"
            + f"date={self.date!r}"
            + ")"
        )


class Character(Base):
    __tablename__ = "character"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    display_name: Mapped[str] = mapped_column()
    clan_name: Mapped[Optional[str]] = mapped_column()
    clan_tag: Mapped[Optional[str]] = mapped_column()
    profile_path: Mapped[str] = mapped_column()

    profile_id = mapped_column(ForeignKey("profile.id"))
    profile: Mapped["Profile"] = relationship(back_populates="characters")
    character_mmrs: Mapped[List["CharacterMMR"]] = relationship(back_populates="character")

    UniqueConstraint(profile_id, display_name, name=CHARACTER_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"Character(id={self.id!r}, "
            + f"profile_id={self.profile_id!r}, "
            + f"display_name={self.display_name!r}, "
            + f"clan_name={self.clan_name!r}, "
            + f"clan_tag={self.clan_tag!r}, "
            + f"profile_path={self.profile_path!r}"
            + ")"
        )


class Profile(Base):
    __tablename__ = "profile"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    profile_id: Mapped[str] = mapped_column()
    realm_id: Mapped[int] = mapped_column()
    region_id: Mapped[int] = mapped_column()

    matches: Mapped[List["Match"]] = relationship(back_populates="profile")
    characters: Mapped[List["Character"]] = relationship(back_populates="profile")
    ladder_members: Mapped[List["LadderMember"]] = relationship(back_populates="profile")

    UniqueConstraint(profile_id, realm_id, region_id, name=PROFILE_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"Profile(id={self.id!r}, "
            + f"profile_id={self.profile_id!r}, "
            + f"realm_id={self.realm_id!r}, "
            + f"region_id={self.region_id!r}"
            + ")"
        )


class Game(Base):
    __tablename__ = "game"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    duration: Mapped[int] = mapped_column()

    matches: Mapped[List["Match"]] = relationship(back_populates="game")


class Match(Base):
    __tablename__ = "match"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    map: Mapped[str] = mapped_column()
    type: Mapped[str] = mapped_column()
    date: Mapped[int] = mapped_column()
    decision: Mapped[str] = mapped_column()
    speed: Mapped[str] = mapped_column()
    duration: Mapped[int] = mapped_column()

    profile_id = mapped_column(ForeignKey("profile.id"))
    profile: Mapped[Profile] = relationship(back_populates="matches")

    game_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("game.id"))
    game: Mapped[Game] = relationship(back_populates="matches")

    UniqueConstraint(profile_id, date, name=MATCH_UNIQUE_CONSTRAINT)

    def __repr__(self) -> str:
        return (
            f"Match(id={self.id!r}, "
            + f"map={self.map!r}, "
            + f"type={self.type!r}, "
            + f"date={self.date!r}, "
            + f"decision={self.decision!r}, "
            + f"speed={self.speed!r}, "
            + f"duration={self.duration!r}, "
            + f"profile_id={self.profile_id!r}"
            + ")"
        )
