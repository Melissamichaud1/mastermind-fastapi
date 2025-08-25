"""
Labels for clarity.
"""

from typing import List, Literal

Digit = int  # 0 -> 7
Code = List[Digit]  # 4 digit guess
GameStatus = Literal["in_progress", "won", "lost"]
Difficulty = Literal["easy", "medium", "hard"]
