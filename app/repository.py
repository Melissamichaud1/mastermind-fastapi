"""
DB-backed repository that mirrors my prev in-memory GameStore API.

Public methods:
- create(secret, attempts, difficulty) -> GameDTO
- get(game_id) -> GameDTO | None
- guess(game_id, attempt) -> GameDTO | None
- get_stats() -> StatsDTO
- reset_stats() -> None
- give_hint(game_id) -> tuple[str, tuple[int, int] | None]

Why: lets me switch from memory to MySQL without changing FastAPI routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import Game as GameORM, Guess as GuessORM, Stats as StatsORM
from .types import Code, Difficulty
from .engine import score_guess, is_win
from .schemas import (
    GuessEntryOut, GameState, StatsOut,
)

from secrets import randbelow

# --- Small DTO builders so routes can stay unchanged ---
# DTOS : Simple objects tht carry data b/w layers of my app; DB -> API resp

def _to_guess_out(g: GuessORM) -> GuessEntryOut:
    return GuessEntryOut(
        guess=g.guess,
        correct_numbers=g.correct_numbers,
        correct_positions=g.correct_positions,
        message=g.message,
        timestamp=g.timestamp.timestamp(),
    )

def _to_game_state(game: GameORM, history: list[GuessORM]) -> GameState:
    return GameState(
        game_id=game.id,
        attempts_left=game.attempts_left,
        status=game.status,           # "in_progress" | "won" | "lost"
        history=[_to_guess_out(h) for h in history],
        difficulty=game.difficulty,   # keep difficulty in API
    )

class DBGameStore:
    """Drop-in replacement for the in-memory GameStore, but using MySQL."""

    def __init__(self, db: Session):
        self.db = db

    # --- Stats helpers ---

    def _get_or_create_stats(self) -> StatsORM:
        stats = self.db.get(StatsORM, 1)
        if not stats:
            stats = StatsORM(id=1)
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)
        return stats

    # --- Public API ---

    def create(self, secret: Code, attempts: int, difficulty: Difficulty = "medium") -> GameState:
        from uuid import uuid4
        gid = str(uuid4())
        now = datetime.utcnow()

        # Create game
        game = GameORM(
            id=gid,
            secret=secret,
            attempts_left=attempts,
            initial_attempts=attempts,
            difficulty=difficulty,
            status="in_progress",
            hint_used=False,
            revealed_positions=[],
            created_at=now,
            updated_at=now,
        )
        self.db.add(game)

        # Update stats.started
        stats = self._get_or_create_stats()
        stats.games_started += 1
        if difficulty == "easy":
            stats.easy_started += 1
        elif difficulty == "hard":
            stats.hard_started += 1
        else:
            stats.medium_started += 1

        self.db.commit()
        self.db.refresh(game)

        return _to_game_state(game, history=[])

    def get(self, game_id: str) -> Optional[GameState]:
        game = self.db.get(GameORM, game_id)
        if not game:
            return None
        history = (
            self.db.execute(select(GuessORM).where(GuessORM.game_id == game_id).order_by(GuessORM.timestamp.asc()))
            .scalars()
            .all()
        )
        return _to_game_state(game, history)

    def guess(self, game_id: str, attempt: Code) -> Optional[GameState]:
        game = self.db.get(GameORM, game_id)
        if not game:
            return None

        if game.status != "in_progress":
            # Return current state without modifying
            history = (
                self.db.execute(select(GuessORM).where(GuessORM.game_id == game_id).order_by(GuessORM.timestamp.asc()))
                .scalars()
                .all()
            )
            return _to_game_state(game, history)

        # Length guard (same behavior as memory store)
        if len(game.secret) != len(attempt):
            raise ValueError(f"Guess must have exactly {len(game.secret)} digits for this game.")

        # Compute feedback
        correct_numbers, correct_positions = score_guess(game.secret, attempt)
        msg = "all incorrect" if (correct_numbers == 0 and correct_positions == 0) else (
            f"{correct_numbers} correct number(s) and {correct_positions} correct location(s)"
        )

        # Append history row
        g = GuessORM(
            game_id=game.id,
            guess=attempt,
            correct_numbers=correct_numbers,
            correct_positions=correct_positions,
            message=msg,
            timestamp=datetime.utcnow(),
        )
        self.db.add(g)

        # Update attempts/status
        game.attempts_left -= 1
        if is_win(game.secret, attempt):
            game.status = "won"
        elif game.attempts_left <= 0:
            game.status = "lost"

        game.updated_at = datetime.utcnow()

        # If terminal transition happened, update stats exactly once
        if game.status in ("won", "lost"):
            self._update_stats_on_end(game, won=(game.status == "won"))

        self.db.commit()

        # Return fresh state
        history = (
            self.db.execute(select(GuessORM).where(GuessORM.game_id == game_id).order_by(GuessORM.timestamp.asc()))
            .scalars()
            .all()
        )
        return _to_game_state(game, history)

    def _update_stats_on_end(self, game: GameORM, won: bool) -> None:
        stats = self._get_or_create_stats()
        if won:
            stats.games_won += 1
            if game.difficulty == "easy":
                stats.easy_won += 1
            elif game.difficulty == "hard":
                stats.hard_won += 1
            else:
                stats.medium_won += 1

            stats.current_streak += 1
            if stats.current_streak > stats.best_streak:
                stats.best_streak = stats.current_streak

            guesses_used = game.initial_attempts - game.attempts_left
            stats.total_guesses_in_wins += guesses_used
            if stats.fastest_win_attempts is None or guesses_used < stats.fastest_win_attempts:
                stats.fastest_win_attempts = guesses_used
        else:
            stats.games_lost += 1
            stats.current_streak = 0

    def get_stats(self) -> StatsOut:
        stats = self._get_or_create_stats()
        avg = (stats.total_guesses_in_wins / stats.games_won) if stats.games_won > 0 else None
        return StatsOut(
            games_started=stats.games_started,
            games_won=stats.games_won,
            games_lost=stats.games_lost,
            current_streak=stats.current_streak,
            best_streak=stats.best_streak,
            average_guesses_to_win=avg,
            fastest_win_attempts=stats.fastest_win_attempts,
            easy_started=stats.easy_started,
            medium_started=stats.medium_started,
            hard_started=stats.hard_started,
            easy_won=stats.easy_won,
            medium_won=stats.medium_won,
            hard_won=stats.hard_won,
        )

    def reset_stats(self) -> None:
        stats = self._get_or_create_stats()
        # Reset by assigning a new instance-like state
        stats.games_started = 0
        stats.games_won = 0
        stats.games_lost = 0
        stats.current_streak = 0
        stats.best_streak = 0
        stats.total_guesses_in_wins = 0
        stats.fastest_win_attempts = None
        stats.easy_started = 0
        stats.medium_started = 0
        stats.hard_started = 0
        stats.easy_won = 0
        stats.medium_won = 0
        stats.hard_won = 0
        self.db.commit()

    def give_hint(self, game_id: str):
        game = self.db.get(GameORM, game_id)
        if not game:
            return ("not_found", None)
        if game.status != "in_progress":
            return ("finished", None)
        if game.hint_used:
            return ("already_used", None)

        total = len(game.secret)
        # Safety: if somehow everything was revealed
        if len(game.revealed_positions) >= total:
            return ("already_used", None)

        # Pick an unrevealed index
        while True:
            idx = randbelow(total)
            if idx not in game.revealed_positions:
                break

        game.hint_used = True
        game.revealed_positions = list(game.revealed_positions) + [idx]
        game.updated_at = datetime.utcnow()
        self.db.commit()

        return ("ok", (idx, game.secret[idx]))

    def get_secret(self, game_id: str):
        """Return the secret code ONLY for finished games; else None."""
        game = self.db.get(GameORM, game_id)
        if not game:
            return None
        if game.status in ("won", "lost"):
            return list(game.secret)  # JSON->python list
        return None
