from typing import List, Optional
import uuid
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class League(Base):
    __tablename__ = "league"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    league_id: Mapped[int] = mapped_column()
    season_id: Mapped[int] = mapped_column()
    queue_id: Mapped[int] = mapped_column()
    team_type: Mapped[int] = mapped_column()

    ladders: Mapped[List["Ladder"]] = relationship(back_populates="league")

    UniqueConstraint(league_id, season_id, queue_id, team_type)

    def __repr__(self) -> str:
        return (
            f"League(id={self.id!r}, "
            + f"league_id={self.league_id!r}, "
            + f"season_id={self.season_id!r}, "
            + f"queue_id={self.queue_id!r}, "
            + f"team_type={self.team_type!r})"
        )


class Ladder(Base):
    __tablename__ = "ladder"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    ladder_id: Mapped[int] = mapped_column()
    min_rating: Mapped[Optional[int]] = mapped_column()
    max_rating: Mapped[Optional[int]] = mapped_column()
    member_count: Mapped[Optional[int]] = mapped_column()

    league_id = mapped_column(ForeignKey("league.id"))
    league: Mapped[League] = relationship(back_populates="ladders")

    UniqueConstraint(league_id, ladder_id)

    def __repr__(self) -> str:
        return (
            f"Ladder(id={self.id!r}, "
            + f"ladder_id={self.ladder_id!r}, "
            + f"min_rating={self.min_rating!r}, "
            + f"max_rating={self.max_rating!r}, "
            + f"member_count={self.member_count!r})"
        )
