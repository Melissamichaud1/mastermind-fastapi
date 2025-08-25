# 🎮 Mastermind (FastAPI + Vanilla JS)

This is my implementation of the classic **Mastermind** code-breaking game, built with:

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Frontend**: HTML, CSS, and vanilla JavaScript
- **Testing**: pytest for backend logic and API routes

---

## 🚀 Features

- Start new games at **Easy, Medium, or Hard** difficulty (3, 4, or 5 digits).
- **Feedback per guess**: numbers correct, positions correct.
- **Duplicate digits allowed**, like the real board game.
- **Creative Extensions**:
  - **Extension 1**: Difficulty selection.
  - **Extension 2**: Scoreboard (tracks wins, losses, streaks, and performance).
  - **Extension 3**: One-time **Hint API** (reveals a single digit/position).
  - **Frontend**:
    - Light/Dark theme toggle (pink themed 🌸).
    - Animated “peg” icons under the title.
    - Clean scoreboard formatting (Overall, Streaks, Performance, By Difficulty).

---

## 🛠️ Requirements

- Python **3.10+**
- Node.js (optional, if using a dev server for frontend)
- Git

Python dependencies are listed in `requirements.txt`.

---

## 📦 Setup Instructions

1. Clone the repo:

```
git clone https://github.com/Melissamichaud1/mastermind-fastapi.git
cd mastermind-fastapi
```

2. Create and activate a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate      # Windows
```

3. Install backend dependencies:

```
pip install -r requirements.txt
```

4. Run the backend server:

```
uvicorn app.main:app --reload
```

By default, FastAPI will run on http://127.0.0.1:8000
Interactive docs are available at http://127.0.0.1:8000/docs

---

## 🌐 Frontend

The frontend lives in the project root (index.html, app.js, CSS inside HTML).

To run locally:

1. Start a local dev server:

```
python3 -m http.server 5173
```

2. Then visit:
   http://127.0.0.1:5173

---

## 📚 API Documentation

FastAPI automatically provides interactive API docs:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

These docs let you:

1. Explore all endpoints:

- **POST `/games`**
  Start a new game. Accepts a `difficulty` query param (`easy`, `medium`, `hard`).

- **GET `/games/{game_id}`**
  Get the current state and history of a specific game.

- **POST `/games/{game_id}/guess`**
  Submit a guess for the game. Validates length & returns feedback.

- **GET `/games/{game_id}/hint`**
  Get one hint (reveals a digit + its position). Only one per game.

- **GET `/stats`**
  View the per-session scoreboard (games started, won, lost, streaks, performance, etc.).

- **POST `/stats/reset`**
  Reset the scoreboard for the current server session.

2. Try requests directly from the browser.
3. View request/response schemas.

---

## 🎯 How to Play

1. Pick a difficulty and click Start Game.
2. Enter guesses separated by spaces (example: 0 1 2 3) and submit.
3. The server responds with:
   Correct numbers: how many digits are present in the secret.
   Correct positions: how many are in the exact correct location.

4. Use strategy + logic to break the code before attempts run out.
5. Optionally, click Get Hint (once per game).

---

## 🧪 Testing

Tests cover both:

1. Core logic (test_engine.py, test_store.py)
2. API endpoints (test_api.py)
3. Run all tests:
   pytest -v

---

## 📖 Thought Process

1. Started with the core engine (score_guess) -> unit tested first.
2. Added store.py to keep game state in memory with locks for thread safety.
3. Built FastAPI endpoints incrementally
4. Wrote pytest tests to validate game logic and API responses.
5. Finally, built a frontend to make the game interactive, focusing on:

- Simplicity (vanilla JS, no frameworks)
- Friendly UI with pink theme
- Clear readability
