"""
Explicit validation & Pydantic models
- Models are used to validate and serialize/deserialize data
exchanged between the client and server.
- Defines the structure of API requests and responses.
"""

from typing import List, Literal
from pydantic import BaseModel, Field, conlist, field_validator

# 1. Represents response when a new game is started
class NewGameResponse(BaseModel):
    game_id: str = Field(..., description="ID; secret is never returned")
    attempts_left: int
    status: Literal["in_progress", "won", "lost"]

# 2. Validates player's guess
class GuessRequest(BaseModel):
    # The guess must be exactly 4 integers, each between 0 and 7
    guess: conlist[int, 4, 4] = Field(
        ..., description="Exactly four digits, each between 0 and 7"
    )

    @field_validator("guess")
    @classmethod
    def validate_digits(game_class, guess_list: List[int]) -> List[int]:
        """
        Pydantic passes in:
        - game_class: reference to the model class (not used, but must be included)
        - guess_list: the actual list of integers the user submitted

        We loop through each digit to make sure it's between 0 and 7.
        """
        index = 0
        while index < len(guess_list):
            digit = guess_list[index]
            if digit < 0 or digit > 7:
                raise ValueError("Each digit must be between 0 and 7 inclusive.")
            index = index + 1

        return guess_list

# 3. Describes the feedback for a single guess
class GuessEntryOut(BaseModel):
    guess: List[int]
    correct_numbers: int
    correct_positions: int
    message: str
    timestamp: float

# 4. Represents the overall state of the game
class GameState(BaseModel):
    game_id: str
    attempts_left: int
    status: Literal["in_progress", "won", "lost"]
    history: List[GuessEntryOut]

# 5. Result of the game
class GuessResponse(BaseModel):
    attempts_left: int
    status: Literal["in_progress", "won", "lost"]
    feedback: GuessEntryOut | None
    secret: List[int] | None = None   # Only filled if game is over
    note: str | None = None
