'''
DB-only Mastermind API

Endpoints:
POST /games                -> start a game
GET  /games/{id}           -> read state & history
POST /games/{id}/guess     -> submit a guess
GET  /games/{id}/hint      -> one-time hint

Extras:
GET  /stats                -> scoreboard
POST /stats/reset          -> reset scoreboard

This version always uses the MySQL-backed repository (DBGameStore).
'''

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .random_client import fetch_code
from .db import get_db                  # SQLAlchemy Session dependency
from .repository import DBGameStore     # DB-backed store
from .bootstrap_db import create_all    # dev-only: create tables

from .schemas import (
    NewGameResponse,
    GuessRequest,
    GuessResponse,
    GameState,
    GuessEntryOut,
    StatsOut,
    HintOut,
)

APP_ENV = os.getenv("APP_ENV", "local")

app = FastAPI(title="Mastermind API (DB)", version="2.0.0")

# Allow everything in dev so the docs and front-end work easily
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Dev convenience: auto-create tables locally ---
if APP_ENV == "local":
    @app.on_event("startup")
    def _dev_create_tables():
        create_all()

# Small factory so routes get a per-request store (bound to the current DB session)
def get_store(session = Depends(get_db)) -> DBGameStore:
    return DBGameStore(session)

# ---------------- Routes ----------------

@app.post("/games", response_model=NewGameResponse, summary="Start a new game")
def start_game(
    difficulty: str = "medium",
    store: DBGameStore = Depends(get_store),
) -> NewGameResponse:
    """
    Difficulty presets:
      easy   -> length=3, attempts=8
      medium -> length=4, attempts=10
      hard   -> length=5, attempts=12
    """
    if difficulty == "easy":
        length, attempts = 3, 8
    elif difficulty == "hard":
        length, attempts = 5, 12
    else:
        difficulty, length, attempts = "medium", 4, 10

    secret = fetch_code(length)                   # random.org w/ secure fallback
    game_state: GameState = store.create(secret, attempts, difficulty)

    return NewGameResponse(
        game_id=game_state.game_id,
        attempts_left=game_state.attempts_left,
        status=game_state.status,
        difficulty=difficulty,
    )

@app.get("/games/{game_id}", response_model=GameState, summary="Get current game state")
def get_game(
    game_id: str,
    store: DBGameStore = Depends(get_store),
) -> GameState:
    game_state = store.get(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_state

@app.post("/games/{game_id}/guess", response_model=GuessResponse, summary="Submit a guess")
def submit_guess(
    game_id: str,
    payload: GuessRequest,
    store: DBGameStore = Depends(get_store),
) -> GuessResponse:
    # repository.guess() performs the length check & updates history/attempts/status
    try:
        updated: GameState = store.guess(game_id, payload.guess)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")

    feedback = updated.history[-1] if updated.history else None

    # Keep UI behavior: when the game ends, include the secret in the response
    secret = None
    if updated.status != "in_progress":
        secret = store.get_secret(game_id)  # NEW: repository helper below

    return GuessResponse(
        attempts_left=updated.attempts_left,
        status=updated.status,
        feedback=feedback,
        secret=secret,
        note=(f"Game {updated.status}. No more guesses allowed."
              if updated.status != "in_progress" else None),
    )

@app.get("/games/{game_id}/hint", response_model=HintOut, summary="Get a one-time hint: Reveals one digit/position")
def get_hint(
    game_id: str,
    store: DBGameStore = Depends(get_store),
) -> HintOut:
    status, data = store.give_hint(game_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Game not found")
    if status == "finished":
        raise HTTPException(status_code=409, detail="Game finished. No hint available.")
    if status == "already_used":
        raise HTTPException(status_code=409, detail="Hint already used for this game.")

    # ok
    position, digit = data
    refreshed = store.get(game_id)
    return HintOut(
        position=position,
        digit=digit,
        attempts_left=refreshed.attempts_left if refreshed else 0,
        note="You used your only hint for this game.",
    )

@app.get("/stats", response_model=StatsOut, summary="Get scoreboard")
def get_stats(store: DBGameStore = Depends(get_store)) -> StatsOut:
    return store.get_stats()

@app.post("/stats/reset", summary="Reset the scoreboard")
def reset_stats(store: DBGameStore = Depends(get_store)) -> dict:
    store.reset_stats()
    return {"message": "Stats reset."}

# ---- Static hosting for the frontend ----
HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).resolve().parent.parent / "app" / "static"

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
