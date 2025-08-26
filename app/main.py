'''
FastAPI endpoints:
POST /games -> start a game (uses random_client + store.create)
POST /games/{id}/guess -> submit a guess (uses store.guess → engine.score_guess)
GET /games/{id} -> read state & history

Extension 2:
GET /stats -> view scoreboard
POST /stats/reset -> reset scoreboard

Extension 3:
GET /games/{game_id}/hint -> get hint
'''

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .random_client import fetch_code
from .store import GameStore
from .schemas import (
    NewGameResponse,
    GuessRequest,
    GuessResponse,
    GameState,
    GuessEntryOut,
    StatsOut, # Extension 2
    HintOut,  # Extension 3
)

app = FastAPI(title="Mastermind API", version="1.0.0")

# Allow everything in dev so the docs and front-end work easily
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Manage game state in memory
store = GameStore()

@app.post("/games", response_model=NewGameResponse, summary="Start a new game")
def start_game(difficulty: str = "medium") -> NewGameResponse:
    """
    Extension #1:
    Start a new game with difficulty level.
    - easy:   length=3, attempts=8
    - medium: length=4, attempts=10 (default)
    - hard:   length=5, attempts=12
    """
    if difficulty == "easy":
        length = 3
        attempts = 8
    elif difficulty == "hard":
        length = 5
        attempts = 12
    else:
        difficulty = "medium"
        length = 4
        attempts = 10

    # Generate secret of variable length
    secret = fetch_code(length)

    # Create game in store with attempts set
    game = store.create(secret, attempts, difficulty)

    return NewGameResponse(
        game_id=game.id,
        attempts_left=game.attempts_left,
        status=game.status,
        difficulty=difficulty, # Extension #1
    )

@app.get("/games/{game_id}", response_model=GameState, summary="Get current game state")
def get_game(game_id: str) -> GameState:
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Convert internal history into API-friendly objects (DTOs)
    history_out: list[GuessEntryOut] = []
    i = 0
    while i < len(game.history):
        guess_entry = game.history[i] # one past guess
        history_out.append(
            GuessEntryOut(
                guess=guess_entry.guess,
                correct_numbers=guess_entry.correct_numbers,
                correct_positions=guess_entry.correct_positions,
                message=guess_entry.message,
                timestamp=guess_entry.timestamp,
            )
        )
        i += 1

    return GameState(
        game_id=game.id,
        attempts_left=game.attempts_left,
        status=game.status,
        history=history_out,
    )

@app.post("/games/{game_id}/guess", response_model=GuessResponse, summary="Submit a guess")
def submit_guess(game_id: str, payload: GuessRequest) -> GuessResponse:
    # 1. Get game first
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # 2) If already finished, reveal secret and return a clear note
    if game.status != "in_progress":
        last = game.history[-1] if game.history else None
        return GuessResponse(
            attempts_left=game.attempts_left,
            status=game.status,
            feedback=GuessEntryOut(
                guess=last.guess,
                correct_numbers=last.correct_numbers,
                correct_positions=last.correct_positions,
                message=last.message,
                timestamp=last.timestamp,
            ) if last else None,
            secret=game.secret,
            note=f"Game {game.status}. No more guesses allowed.",
        )

    # Extension #1 - Length check
    required_length = len(game.secret)
    if len(payload.guess) != required_length:
        raise HTTPException(
            status_code=400,
            detail=f"Your guess must have exactly {required_length} digits for this difficulty."
        )

    # 3. Apply the guess once (this decrements attempts and appends feedback)
    try:
        game = store.guess(game_id, payload.guess)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # 4. Defensive: ensure feedback exists
    if not game.history:
        raise HTTPException(status_code=500, detail="Internal error: no feedback recorded")

    # The most recent history item is the feedback for this guess
    feedback = game.history[-1]

    # 5) If this guess ended the game, include secret + note
    if game.status != "in_progress":
        return GuessResponse(
            attempts_left=game.attempts_left,
            status=game.status,
            feedback=GuessEntryOut(
                guess=feedback.guess,
                correct_numbers=feedback.correct_numbers,
                correct_positions=feedback.correct_positions,
                message=feedback.message,
                timestamp=feedback.timestamp,
            ),
            secret=game.secret,
            note=f"Game {game.status}. No more guesses allowed.",
        )

    # 6. Otherwise, normal in-progress response
    return GuessResponse(
        attempts_left=game.attempts_left,
        status=game.status,
        feedback=GuessEntryOut(
            guess=feedback.guess,
            correct_numbers=feedback.correct_numbers,
            correct_positions=feedback.correct_positions,
            message=feedback.message,
            timestamp=feedback.timestamp,
        ),
    )

# Extension 2: Endpoint to view scoreboard
@app.get("/stats", response_model = StatsOut, summary="Get per-session scoreboard")
def get_stats() -> StatsOut:
    stats = store.get_stats()
    average = None
    if stats.games_won > 0:
        average = stats.total_guesses_in_wins / stats.games_won

    return StatsOut(
        games_started=stats.games_started,
        games_won=stats.games_won,
        games_lost=stats.games_lost,
        current_streak=stats.current_streak,
        best_streak=stats.best_streak,
        average_guesses_to_win=average,
        fastest_win_attempts=stats.fastest_win_attempts,
        easy_started=stats.easy_started,
        medium_started=stats.medium_started,
        hard_started=stats.hard_started,
        easy_won=stats.easy_won,
        medium_won=stats.medium_won,
        hard_won=stats.hard_won,
    )

# Extension 2: Endpoint to reset scoreboard
@app.post("/stats/reset", summary="Reset the scoreboard")
def reset_stats() -> dict:
    store.reset_stats()
    return {"message": "Stats reset for this server session."}

# Extension 3: Get a hint
@app.get("/games/{game_id}/hint", response_model=HintOut, summary="Get a one-time hint: Reveals one digit/position")
def get_hint(game_id: str) -> HintOut:
    result = store.give_hint(game_id)
    status = result[0]
    data = result[1]

    if status == "not_found":
        raise HTTPException(status_code=404, detail="Game not found")

    if status == "finished":
        raise HTTPException(status_code=409, detail="Game finished. No hint available.")

    if status == "already_used":
        raise HTTPException(status_code=409, detail="Hint already used for this game.")

    # status == "ok"
    position = data[0]
    digit = data[1]

    # Read attempts_left to include in response
    game = store.get(game_id)

    return HintOut(
        position=position,
        digit=digit,
        attempts_left=game.attempts_left,
        note="You used your only hint for this game."
    )

# ---- Static hosting for the frontend ----
# Point to the repo's /static folder (index.html, app.js, fonts/, etc.)
HERE = Path(__file__).resolve().parent          # /.../app
STATIC_DIR = HERE / "static"                    # /.../app/static

if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).resolve().parent.parent / "app" / "static"

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
