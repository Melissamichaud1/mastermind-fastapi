"""
Testing in-memory store
- Create a game, make guesses, and check status/attempts/history, etc.
"""

from app.store import GameStore
from app.types import Difficulty

def test_store_create_and_guess_basic():
    store = GameStore()

    # Secret is hardcoded so we know what outcome should be
    secret = [1,2,3,4]
    attempts = 3
    difficulty: Difficulty = "medium"

    game = store.create(secret, attempts, difficulty)
    game_id = game.id

    # Game starts in progress with correct attempts
    assert game.status == "in_progress"
    assert game.attempts_left == 3

    # Wrong guess, same length -> attempts should decrement, history increments
    store.guess(game_id, [0,0,0,0])
    game_after = store.get(game_id)
    assert game_after.attempts_left == 2
    assert len(game_after.history) == 1
    assert game_after.status == "in_progress"

    # Winning guess ends the game
    store.guess(game_id, [1, 2, 3, 4])
    game_win = store.get(game_id)
    assert game_win.status == "won"
    # attempts should be 1 now (3 start -> 1 wrong -> 1 win)
    assert game_win.attempts_left == 1

def test_store_stats_update_on_win_and_loss():
    store = GameStore()

    # Game A: win in 2 guesses
    game_a = store.create([1,2,3], attempts=5, difficulty="easy")
    store.guess(game_a.id, [1,0,0]) # wrong
    store.guess(game_a.id, [1,2,3]) # win

    stats_after_win = store.get_stats()
    assert stats_after_win.games_started == 1
    assert stats_after_win.games_won == 1
    assert stats_after_win.games_lost == 0
    assert stats_after_win.current_streak >= 1
    assert stats_after_win.total_guesses_in_wins >= 2
    assert stats_after_win.fastest_win_attempts is not None

    # Game B: force a loss (use only 1 attempt so a wrong guess ends it)
    game_b = store.create([7,7,7,7], attempts=1, difficulty="medium")
    store.guess(game_b.id, [0,0,0,0])  # wrong -> lost

    stats_final = store.get_stats()
    assert stats_final.games_started == 2
    assert stats_final.games_won == 1
    assert stats_final.games_lost == 1
