"""
SQLAlchemy ORM models for MySQL storage.

Tables:
- games: one row per game (secret stored as JSON, plus counters/flags)
- guesses: one row per guess (history)
- stats: single-row scoreboard (session-level stats; mirrors your in-memory Stats)

Why JSON?
- Secret and guesses are small arrays of ints; JSON is simple & clear.
- MySQL (5.7+/8.0+) supports JSON type natively.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, DateTime, Enum, Boolean, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base
from .types import Difficulty, GameStatus  # reuse my literals for clarity

class Game(Base):
    __tablename__ = "games"

    # UUIDs generated in code; stored as strings
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Secret code (list[int], digits 0..7); stored as JSON for simplicity
    secret: Mapped[list[int]] = mapped_column(JSON, nullable=False)

    # Attempts tracking
    attempts_left: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    initial_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # State & difficulty
    status: Mapped[GameStatus] = mapped_column(
        Enum("in_progress", "won", "lost", name="game_status"),
        nullable=False,
        default="in_progress",
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum("easy", "medium", "hard", name="difficulty"),
        nullable=False,
        default="medium",
    )

    # Hint info
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Keep track of which indices we revealed (tiny array)
    revealed_positions: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship: a game has many guesses (history)
    guesses: Mapped[list["Guess"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Guess.timestamp.asc()",
    )

class Guess(Base):
    __tablename__ = "guesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to games.id
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    game: Mapped[Game] = relationship(back_populates="guesses")

    # The player's guess (list[int])
    guess: Mapped[list[int]] = mapped_column(JSON, nullable=False)

    # Engine output
    correct_numbers: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamp (float in memory; datetime here)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

# “Session scoreboard” mirrors my previous in-memory Stats.
# For simplicity: store exactly one row with id=1.
class Stats(Base):
    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    games_started: Mapped[int] = mapped_column(Integer, default=0)
    games_won: Mapped[int] = mapped_column(Integer, default=0)
    games_lost: Mapped[int] = mapped_column(Integer, default=0)

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)

    total_guesses_in_wins: Mapped[int] = mapped_column(Integer, default=0)
    fastest_win_attempts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # per-difficulty counters
    easy_started: Mapped[int] = mapped_column(Integer, default=0)
    medium_started: Mapped[int] = mapped_column(Integer, default=0)
    hard_started: Mapped[int] = mapped_column(Integer, default=0)

    easy_won: Mapped[int] = mapped_column(Integer, default=0)
    medium_won: Mapped[int] = mapped_column(Integer, default=0)
    hard_won: Mapped[int] = mapped_column(Integer, default=0)
