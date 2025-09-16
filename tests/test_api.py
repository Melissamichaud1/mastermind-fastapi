"""
Testing API via TestClient
- Trick: temporarily replace random_client.fetch_code so the secret is predictable.
- Tool: pytest's "monkeypatch" fixture does that for just one test at a time.
"""

import pytest
import app.random_client as random_client
import app.main as app_main

# To control the secret during tests, we patch `app_main.fetch_code`.

# 1. Helper: Create a fake fetch_code function that returns a known secret for each length
def make_fake_fetch_code():
    """
    Returns a function that ignores randomness and gives us:
      - length 3 -> [1, 2, 3]  (EASY)
      - length 4 -> [0, 1, 2, 3]  (MEDIUM)
      - length 5 -> [0, 1, 2, 3, 4]  (HARD)
    """
    def fake_fetch_code(length: int):
        if length == 3:
            return [1, 2, 3]
        elif length == 4:
            return [0, 1, 2, 3]
        elif length == 5:
            return [0, 1, 2, 3, 4]
        # fallback: zeros of requested length
        return [0 for _ in range(length)]
    return fake_fetch_code


def test_start_easy_and_win_with_fixed_secret(client, monkeypatch):
    """
    Flow:
    1) Start EASY game; secret is [1,2,3] due to patch.
    2) Wrong-length guess -> 400.
    3) Valid-length wrong guess -> 200 + feedback.
    4) Winning guess -> 'won' and secret revealed.
    """
    fake_fetch_code = make_fake_fetch_code()
    # Patch the bound symbol that main.py actually uses
    monkeypatch.setattr(app_main, "fetch_code", fake_fetch_code)

    # Start easy game (length = 3, attempts = 8)
    response = client.post("/games?difficulty=easy")
    assert response.status_code == 200
    new_game = response.json()
    game_id = new_game["game_id"]

    # Wrong length -> 400
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 400

    # Valid-length but wrong guess
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 0, 0]})
    assert response.status_code == 200
    body = response.json()
    assert "feedback" in body
    assert body["status"] in ("in_progress", "lost", "won")

    # Win
    response = client.post(f"/games/{game_id}/guess", json={"guess": [1, 2, 3]})
    assert response.status_code == 200
    final = response.json()
    assert final["status"] == "won"
    assert final["secret"] == [1, 2, 3]


def test_cannot_guess_after_game_finished(client, monkeypatch):
    """
    Flow:
    1) Start MEDIUM game; secret [0,1,2,3].
    2) Win in one guess.
    3) Guess again -> status stays 'won', attempts_left unchanged.
    """
    fake_fetch_code = make_fake_fetch_code()
    # Again: patch app_main.fetch_code, not the module
    monkeypatch.setattr(app_main, "fetch_code", fake_fetch_code)

    # Start medium
    response = client.post("/games?difficulty=medium")
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Win
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 200
    first = response.json()
    assert first["status"] == "won"
    assert first["secret"] == [0, 1, 2, 3]
    attempts_after_win = first["attempts_left"]

    # Try again after finished
    response = client.post(f"/games/{game_id}/guess", json={"guess": [0, 1, 2, 3]})
    assert response.status_code == 200
    second = response.json()
    assert second["status"] == "won"
    assert second["attempts_left"] == attempts_after_win
    if "note" in second:
        assert "No more guesses" in second["note"]


def test_stats_after_a_loss(client, monkeypatch):
    """
    Flow:
    1) Reset scoreboard.
    2) Start MEDIUM game (secret [0,1,2,3]).
    3) Make 10 wrong guesses to force a loss.
    4) Check /stats reflects a loss.
    """
    fake_fetch_code = make_fake_fetch_code()
    # Patch the symbol the app calls
    monkeypatch.setattr(app_main, "fetch_code", fake_fetch_code)

    # Reset stats
    r = client.post("/stats/reset")
    assert r.status_code == 200

    # Start medium
    start = client.post("/games?difficulty=medium")
    assert start.status_code == 200
    gid = start.json()["game_id"]

    # 10 wrong guesses
    for _ in range(10):
        r = client.post(f"/games/{gid}/guess", json={"guess": [4, 4, 4, 4]})
        assert r.status_code == 200

    # Check stats
    stats_resp = client.get("/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["games_started"] >= 1
    assert stats["games_lost"] >= 1
    assert stats["games_won"] == 0
