"""
In-memory store
Holds game state in memory.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4
from time import time
from threading import RLock
from secrets import randbelow

from .types import Code, GameStatus, Difficulty
from .engine import score_guess, is_win

@dataclass
class GuessEntry:
    guess: Code
    correct_numbers: int
    correct_positions: int
    message: str
    timestamp: float

@dataclass
class Game:
    id: str
    secret: Code
    attempts_left: int = 10
    status: GameStatus = "in_progress"
    history: List[GuessEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)
    # Extension 2: store starting attempts to calculate guesses used in wins
    initial_attempts: int = 10
    difficulty: Difficulty = "medium"
    # Extension 3: get a hint
    hint_used: bool = False
    revealed_positions: List[int] = field(default_factory=list)

# Extension 2: Scoreboard structure
@dataclass
class Stats:
    games_started: int = 0
    games_won: int = 0
    games_lost: int = 0

    current_streak: int = 0
    best_streak: int = 0

    total_guesses_in_wins: int = 0
    fastest_win_attempts: Optional[int] = None

    # per-difficulty counters
    easy_started: int = 0
    medium_started: int = 0
    hard_started: int = 0
    easy_won: int = 0
    medium_won: int = 0
    hard_won: int = 0


class GameStore:
    def __init__(self) -> None:
        self._games: Dict[str, Game] = {}
        self._lock = RLock()
        # Extension 2: initialize stats
        self._stats = Stats()

    def create(self, secret: Code, attempts: int, difficulty: Difficulty = "medium") -> Game:
        new_id = str(uuid4())
        game = Game(
            id=new_id,
            secret=secret,
            attempts_left=attempts,
            initial_attempts=attempts,  # Extension 2
            difficulty=difficulty,      # Extension 2
        )
        with self._lock:
            self._games[new_id] = game

            # Extension 2: Update scoreboard when game is created
            self._stats.games_started += 1
            if difficulty == "easy":
                self._stats.easy_started += 1
            elif difficulty == "hard":
                self._stats.hard_started += 1
            else:
                self._stats.medium_started += 1
        return game

    def get(self, game_id: str) -> Optional[Game]:
        with self._lock:
            return self._games.get(game_id)

    def guess(self, game_id: str, attempt: Code) -> Optional[Game]:
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return None

            if game.status != "in_progress":
                # If game already ended, just return it (ignore extra guesses)
                return game

            # --- length guard ---
            if len(game.secret) != len(attempt):
                raise ValueError(f"Guess must have exactly {len(game.secret)} digits for this game.")

            old_status = game.status

            # Get the feedback using the engine
            result = score_guess(game.secret, attempt)
            correct_numbers = result[0]
            correct_positions = result[1]

            # Build a message without revealing which digits are correct
            if correct_numbers == 0 and correct_positions == 0:
                msg = "all incorrect"
            else:
                msg = (
                    str(correct_numbers)
                    + " correct number(s) and "
                    + str(correct_positions)
                    + " correct location(s)"
                )

            # Save to history
            entry = GuessEntry(
                guess=attempt,
                correct_numbers=correct_numbers,
                correct_positions=correct_positions,
                message=msg,
                timestamp=time(),
            )
            game.history.append(entry)

            # Update attempts and status
            game.attempts_left -= 1

            if is_win(game.secret, attempt):
                game.status = "won"
            else:
                if game.attempts_left <= 0:
                    game.status = "lost"

            game.updated_at = time()

            # Update scoreboard exactly once when we detect a transition
            # If we moved from "in_progress" to either "won" or "lost", update stats now.
            if old_status == "in_progress" and game.status in ("won", "lost"):
                self._update_stats_on_end(game, won=(game.status == "won"))

            return game

    # Extension 2: Helper updates scoreboard exactly once per game
    def _update_stats_on_end(self, game: Game, won: bool) -> None:
        if won:
            self._stats.games_won += 1

            # per-difficulty wins
            if game.difficulty == "easy":
                self._stats.easy_won += 1
            elif game.difficulty == "hard":
                self._stats.hard_won += 1
            else:
                self._stats.medium_won += 1

            # streaks
            self._stats.current_streak += 1
            if self._stats.current_streak > self._stats.best_streak:
                self._stats.best_streak = self._stats.current_streak

            # guesses used
            guesses_used = game.initial_attempts - game.attempts_left
            self._stats.total_guesses_in_wins += guesses_used
            if self._stats.fastest_win_attempts is None or guesses_used < self._stats.fastest_win_attempts:
                self._stats.fastest_win_attempts = guesses_used
        else:
            self._stats.games_lost += 1
            self._stats.current_streak = 0

    # Extension 2: public API for stats
    def get_stats(self) -> Stats:
        return self._stats

    def reset_stats(self) -> None:
        with self._lock:
            self._stats = Stats()

    # Extension 3: Generate one hint (position, digit) for a game
    def give_hint(self, game_id: str):
        """
        Returns a tuple like ("ok", (position, digit))
        Or: ("finished", None) if game ended
            ("already_used", None) if hint was used
            ("not_found", None) if no game
        """
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return ("not_found", None)

            # If the game already ended, we do not provide a hint
            if game.status != "in_progress":
                return ("finished", None)

            # Only one hint per game
            if game.hint_used:
                return ("already_used", None)

            # Choose a random position we have not revealed yet
            total = len(game.secret)

            # Safety: if somehow everything was revealed
            if len(game.revealed_positions) >= total:
                return ("already_used", None)

            # Continue until we find an index not yet revealed
            while True:
                index = randbelow(total) # 0 -> total-1
                # check if this index is already revealed
                already_revealed = False
                j = 0
                while j < len(game.revealed_positions):
                    if game.revealed_positions[j] == index:
                        already_revealed = True
                        break
                    j += 1

                if not already_revealed:
                    break

            # Mark it used and record the index
            game.hint_used = True
            game.revealed_positions.append(index)
            game.updated_at = time()

            digit = game.secret[index]
            return ("ok", (index, digit))
