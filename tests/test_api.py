"""
Testing API via TestClient
- Trick: temporarily replace random_client.fetch_code so the secret is predictable.
- Tool: pytest's "monkeypatch" fixture does that for just one test at a time.
"""

from fastapi.testclient import TestClient
from app.main import app
# Import the module that contains fetch_code so we can patch it
import app.main as main_module

# 1. Helper: Create a fake fetch_code function that returns a known secret for each length
def make_fake_fetch_code():
    """
    Returns a function that ignores randomness and gives us:
      - length 3 -> [1, 2, 3]  (EASY)
      - length 4 -> [0, 1, 2, 3]  (MEDIUM)
      - length 5 -> [0, 1, 2, 3, 4]  (HARD)
    """
    def fake_fetch_code(length: int):
        # Build the list manually so it’s obvious what’s happening
        if length == 3:
            return [1, 2, 3]
        elif length == 4:
            return [0, 1, 2, 3]
        elif length == 5:
            return [0, 1, 2, 3, 4]
        else:
            # Fallback: just return zeros of the requested length
            # (Not used in current code, but safe.)
            result = []
            i = 0
            while i < length:
                result.append(0)
                i += 1
            return result

    return fake_fetch_code

client = TestClient(app)

def test_start_easy_and_win_with_fixed_secret(monkeypatch):
    """
    Flow tested:
    1) Start an EASY game. Because we patch fetch_code, we know the secret is [1, 2, 3].
    2) Try a wrong-length guess -> expect HTTP 400.
    3) Try a valid-length but wrong guess -> expect 200 with feedback (still in_progress or lost).
    4) Try the winning guess -> expect status 'won' and the secret revealed.
    """

    # 1) Replace random_client.fetch_code with our fake function for this test only
    fake_fetch_code = make_fake_fetch_code()
    monkeypatch.setattr(main_module, "fetch_code", fake_fetch_code)

    # Start easy game (length = 3, attempts = 8)
    response = client.post("/games?difficulty=easy")
    assert response.status_code == 200
    new_game = response.json()

    # Take the game_id from the response so we can submit guesses to this game
    game_id = new_game["game_id"]

    # 2) Submit a wrong-length guess (length 4 instead of 3) -> the API should reject it with 400
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 400

    # 3) Submit a valid-length but wrong guess -> should be 200, but game still in progress
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 0, 0]})
    assert response.status_code == 200
    body = response.json()
    # We can check that feedback exists and status is either in_progress or lost (but likely in_progress)
    assert "feedback" in body
    assert body["status"] in ("in_progress", "lost", "won")

    # 4) Submit the winning guess (we know the secret is [1, 2, 3])
    response = client.post(f"/games/{game_id}/guess", json={"guess": [1, 2, 3]})
    assert response.status_code == 200
    final = response.json()
    assert final["status"] == "won"
    # On finish, our API returns the secret
    assert final["secret"] == [1, 2, 3]

def test_cannot_guess_after_game_finished(monkeypatch):
    """
    Flow tested:
    1) Start a MEDIUM game. With our patch, secret is [0, 1, 2, 3].
    2) Win in one guess.
    3) Try to guess again after game is finished -> API should NOT allow progress (status remains 'won'),
       and attempts_left should NOT go down further.
    """

    # Patch randomness again for this test
    fake_fetch_code = make_fake_fetch_code()
    monkeypatch.setattr(main_module, "fetch_code", fake_fetch_code)

    # Start medium game (length = 4, attempts = 10)
    response = client.post("/games?difficulty=medium")
    assert response.status_code == 200
    new_game = response.json()
    game_id = new_game["game_id"]

    # Win right away using the known secret [0, 1, 2, 3]
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 200
    first = response.json()
    assert first["status"] == "won"
    assert first["secret"] == [0, 1, 2, 3]

    # Record attempts_left after the winning guess (should be 9, since it starts at 10 and we used 1 guess)
    attempts_after_win = first["attempts_left"]

    # Try guessing again after game finished
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 200
    second = response.json()

    # The game should still be 'won' and attempts_left should not change
    assert second["status"] == "won"
    assert second["attempts_left"] == attempts_after_win
    # Some implementations also include a "note" telling you no more guesses are allowed
    if "note" in second:
        assert "No more guesses" in second["note"]

def test_stats_after_a_loss(monkeypatch):
    """
    Flow tested:
    1) Reset the scoreboard.
    2) Start a MEDIUM game (secret will be [0,1,2,3] due to our patch).
    3) Make 10 wrong guesses to force a loss.
    4) Check /stats: games_started=1, games_lost>=1 (exact value depends on store update timing).
    """

    # Patch randomness again
    fake_fetch_code = make_fake_fetch_code()
    monkeypatch.setattr(main_module, "fetch_code", fake_fetch_code)

    # 1) Reset stats to a clean state
    reset = client.post("/stats/reset")
    assert reset.status_code == 200

    # 2) Start a new medium game
    start = client.post("/games?difficulty=medium")
    assert start.status_code == 200
    gid = start.json()["game_id"]

    # 3) Make up to 10 wrong guesses (we know the secret is [0,1,2,3], so guessing [4,4,4,4] is wrong)
    #    We'll loop exactly 10 times to use up attempts.
    tries = 0
    while tries < 10:
        r = client.post(f"/games/{gid}/guess", json={"guess": [4, 4, 4, 4]})
        # Even on last guess, the API responds 200 with the final state
        assert r.status_code == 200
        tries = tries + 1

    # 4) Check stats
    stats_resp = client.get("/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()

    # games_started should be at least 1 (exactly 1 here since we reset first)
    assert stats["games_started"] >= 1
    # We expect at least one loss since we made 10 incorrect guesses
    assert stats["games_lost"] >= 1
    # games_won should be 0 for this test
    assert stats["games_won"] == 0
