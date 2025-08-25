"""
Testing pure game logic.
"""

from app.engine import score_guess, is_win

def test_score_guess_no_matches():
    # secret has digits 0,1,2,3
    secret = [0,1,2,3]
    # guess has digits 4,5,6,7
    guess = [4,5,6,7]

    result = score_guess(secret, guess)
    correct_numbers = result[0]
    correct_positions = result[1]

    assert correct_numbers == 0
    assert correct_positions == 0

def test_score_guess_some_position_matches():
    secret = [0,1,3,5]
    guess = [0,2,4,6]

    result = score_guess(secret, guess)
    correct_numbers = result[0]
    correct_positions = result[1]

    # Only the first position matches (0)
    assert correct_positions == 1
    # Only one digit overlaps at all (0)
    assert correct_numbers == 1

def test_score_guess_with_duplicates():
    # Duplicates are allowed in secret and guess
    secret = [2,2,5,5]
    guess = [2,5,2,5]

    result = score_guess(secret, guess)
    correct_numbers = result[0]
    correct_positions = result[1]

    # Digits overlap: there are two 2s and two 5s
    # Minimum per digit (2 and 5) adds up to 4
    assert correct_numbers == 4
    # Exact position matches: first and last positions
    assert correct_positions == 2

def test_is_win_true_and_false():
    assert is_win([1,2,3,4], [1,2,3,4]) is True
    assert is_win([1,2,3,4], [1,2,3,5]) is False
