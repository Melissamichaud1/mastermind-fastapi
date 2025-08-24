"""
In-memory store
Holds game state in memory.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4
from time import time
from threading import RLock

from .types import Code, GameStatus
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

class GameStore:
    def __init__(self) -> None:
        self._games: Dict[str, Game] = {}
        self._lock = RLock()

    def create(self, secret: Code, attempts: int) -> Game:
        new_id = str(uuid4())
        game = Game(id=new_id, secret=secret, attempts_left=attempts)
        with self._lock:
            self._games[new_id] = game
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
                # IF game already ended, just return it (ignore extra guesses)
                return game

            # --- length guard ---
            if len(game.secret) != len(attempt):
            # Don’t modify game if guess length is wrong
                return game

            # Get the feedback using the engine
            result = score_guess(game.secret, attempt)
            correct_numbers = result[0]
            correct_positions = result[1]

            # --- duplicate guard here ---
            if game.history:
                last = game.history[-1]
                if last.guess == attempt and game.status == "in_progress":
                    return game

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
            return game
