'''
FastAPI endpoints:
POST /games → start a game (uses random_client + store.create)
POST /games/{id}/guess → submit a guess (uses store.guess → engine.score_guess)
GET /games/{id} → read state & history
'''

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .random_client import fetch_code
from .store import GameStore
from .schemas import (
    NewGameResponse,
    GuessRequest,
    GuessResponse,
    GameState,
    GuessEntryOut,
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

store = GameStore()

@app.post("/games", response_model=NewGameResponse, summary="Start a new game")
def start_game() -> NewGameResponse:
    secret = fetch_code()
    game = store.create(secret)
    return NewGameResponse(
        game_id=game.id,
        attempts_left=game.attempts_left,
        status=game.status,
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

    # 3. Apply the guess once (this decrements attempts and appends feedback)
    game = store.guess(game_id, payload.guess)

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
