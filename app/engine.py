"""
Pure game logic (no HTTP, no storage).
We compute two feedback numbers for each guess:
- correct_positions: how many indices are exactly correct (right number, right place)
- correct_numbers: total count of digits that appear in the secret (including the correct_positions)
and including those already in correct position.

We allow duplicates in the secret.
"""

from typing import Tuple
from .types import Code

def score_guess(secret: Code, guess: Code) -> Tuple[int, int]:
    """
    Example:
      secret = [0, 1, 3, 5]
      guess  = [0, 2, 4, 6]
      correct_positions = 1  (the first 0 matches)
      correct_numbers   = 1  (only one digit, '0', appears in both)
      Returns a tuple: (correct_numbers, correct_positions)
    """

    # 0, Validate lengths match
    n = len(secret)
    if n == 0 or len(guess) != n:
        raise ValueError("Secret and guess must be the same non-zero length.")

    # 1. Count exact position matches --> correct_positions
    correct_positions = 0
    i = 0
    while i < n:
        if secret[i] == guess[i]:
            correct_positions += 1
        i += 1

    # 2. Count how many digits appear anywhere in both lists --> correct_numbers
    secret_counts = [0,0,0,0,0,0,0,0]
    guess_counts = [0,0,0,0,0,0,0,0]

    # Fill counts for secret
    idx = 0
    while idx < n:
        digit = secret[idx]
        # ignore out of range
        if digit >= 0 and digit <= 7:
            secret_counts[digit] += 1
        idx += 1

    # Fill counts for guess
    idx = 0
    while idx < n:
        digit = guess[idx]
        if digit >= 0 and digit <= 7:
            guess_counts[digit] += 1
        idx += 1

    # Overlap is the sum of the smaller count for each digit
    correct_numbers = 0
    digit = 0
    while digit <= 7:
        # add the minimum of the two counts
        if secret_counts[digit] < guess_counts[digit]:
            correct_numbers += secret_counts[digit]
        else:
            correct_numbers += guess_counts[digit]
        digit += 1

    return (correct_numbers, correct_positions)

def is_win(secret: Code, guess: Code) -> bool:
    """
    Win = all digits match in order, for all positions.
    Works for any length, as long as lengths match.
    """
    n = len(secret)
    if n == 0 or len(guess) != n:
        return False

    i = 0
    while i < n:
        if secret[i] != guess[i]:
            return False
        i += 1
    return True
