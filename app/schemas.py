"""
Explicit validation & Pydantic models
- Models are used to validate and serialize/deserialize data
  exchanged between the client and server.
- Defines the structure of API requests and responses.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

# 1. Represents response when a new game is started
class NewGameResponse(BaseModel):
    game_id: str = Field(..., description="Unique ID for the game; secret is never returned")
    attempts_left: int = Field(..., description="How many guesses remain")
    status: Literal["in_progress", "won", "lost"] = Field(..., description="Current state of the game")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="Chosen difficulty level")

# 2. Validates player's guess
class GuessRequest(BaseModel):
    guess: List[int] = Field(
        ..., description="A list of digits (length depends on difficulty). Each digit must be between 0 and 7."
    )

    @field_validator("guess")
    @classmethod
    def validate_digits(cls, guess_list: List[int]) -> List[int]:
        """
        We only check that each item is an integer between 0 and 7.
        We do not check the length here because the length depends on the game's difficulty.
        The route will check the length against the game's secret.
        """
        index = 0
        while index < len(guess_list):
            digit = guess_list[index]
            if digit < 0 or digit > 7:
                raise ValueError("Each digit must be between 0 and 7 inclusive.")
            index += 1
        return guess_list

    model_config = {
        "json_schema_extra": {
            "examples": [
                { "guess": [0, 1, 2, 3] },        # medium (default)
                { "guess": [0, 1, 2] },           # easy
                { "guess": [0, 1, 2, 3, 4] },     # hard
            ]
        }
    }

# 3. Describes the feedback for a single guess
class GuessEntryOut(BaseModel):
    guess: List[int] = Field(..., description="The player's guess")
    correct_numbers: int = Field(..., description="How many digits are correct (any position)")
    correct_positions: int = Field(..., description="How many digits are in the correct position")
    message: str = Field(..., description="Feedback message")
    timestamp: float = Field(..., description="When the guess was made")

# 4. Represents the overall state of the game
class GameState(BaseModel):
    game_id: str = Field(..., description="Unique ID for the game")
    attempts_left: int = Field(..., description="How many guesses remain")
    status: Literal["in_progress", "won", "lost"] = Field(..., description="Current state of the game")
    history: List[GuessEntryOut] = Field(..., description="All guesses made so far with feedback")

# 5. Result of a guess (or end of the game)
class GuessResponse(BaseModel):
    attempts_left: int = Field(..., description="How many guesses remain")
    status: Literal["in_progress", "won", "lost"] = Field(..., description="Current state of the game")
    feedback: GuessEntryOut | None = Field(None, description="Feedback from the latest guess")
    secret: List[int] | None = Field(None, description="The secret code (only revealed if game is over)")
    note: str | None = Field(None, description="Extra note (ex. 'Game lost. No more guesses.')")

# 6. Extension 2: Response schema for scoreboard
class StatsOut(BaseModel):
    games_started: int = Field(..., description="Total games started this session")
    games_won: int = Field(..., description="Total games won this session")
    games_lost: int = Field(..., description="Total games lost this session")

    current_streak: int = Field(..., description="Current consecutive wins")
    best_streak: int = Field(..., description="Best consecutive wins")

    average_guesses_to_win: Optional[float] = Field(
        None, description="Average number of guesses used in wins"
    )
    fastest_win_attempts: Optional[int] = Field(
        None, description="Fewest guesses taken to win a game"
    )

    easy_started: int = Field(..., description="Games started on Easy difficulty")
    medium_started: int = Field(..., description="Games started on Medium difficulty")
    hard_started: int = Field(..., description="Games started on Hard difficulty")

    easy_won: int = Field(..., description="Games won on Easy difficulty")
    medium_won: int = Field(..., description="Games won on Medium difficulty")
    hard_won: int = Field(..., description="Games won on Hard difficulty")

# 7. Extension 3: Response schema for hint
class HintOut(BaseModel):
    position: int = Field(..., description="Index in the code")
    digit: int = Field(..., description="Digit at that index")
    attempts_left: int = Field(..., description="Guesses remaining")
    note: str = Field(..., description="Extra info, ex. 'You used your only hint!")
