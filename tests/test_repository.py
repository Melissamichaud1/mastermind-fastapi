# tests/test_repository.py
from app.repository import DBGameStore
from app.engine import is_win

def test_repository_flow(db_session, monkeypatch):
    # Determined secret
    monkeypatch.setattr("app.random_client.fetch_code", lambda length: [1,2,3,4])

    repo = DBGameStore(db_session)

    # Create
    state = repo.create(secret=[1,2,3,4], attempts=10, difficulty="medium")
    gid = state.game_id

    # Guess (not win)
    state = repo.guess(gid, [1,9,9,9])
    assert state.status == "in_progress"

    # Win
    state = repo.guess(gid, [1,2,3,4])
    assert state.status == "won"

    # Stats reflect win
    stats = repo.get_stats()
    assert stats.games_started == 1
    assert stats.games_won == 1
    assert stats.current_streak == 1
