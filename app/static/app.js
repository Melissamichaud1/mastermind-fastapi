// If we're on localhost/127.0.0.1, talk to the local dev server.
// Otherwise, use same-origin (empty prefix) so /games, /stats, etc. hit this host.
const API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "";

let gameId = null; // holds the active game's ID
let difficulty = "medium"; // default difficulty if not selected

/* ---------- helpers ---------- */

// Convert a string like "0 1 2 3" into an array [0,1,2,3]
function parseGuess(inputText) {
  const parts = inputText.trim().split(/\s+/); // split on spaces
  const list = [];
  let i = 0;
  while (i < parts.length) {
    const n = Number(parts[i]); // turn each part into a number
    if (!Number.isNaN(n)) list.push(n); // only add if it’s a valid number
    i = i + 1;
  }
  return list;
}

// Format an array like [1,2,3] into a pretty string "[1, 2, 3]"
function formatGuessArray(arr) {
  if (!Array.isArray(arr)) return "[—]";
  return "[" + arr.join(", ") + "]";
}

// Show an error message and make the box visible
function setError(msg) {
  const box = document.getElementById("last-feedback");
  box.textContent = msg;
  box.style.display = "block";
}

// Hide and clear the error message
function clearError() {
  const box = document.getElementById("last-feedback");
  box.textContent = "";
  box.style.display = "none";
}

// Updates the "Last Guess" card with feedback from the server
function setLastGuessCard(feedback) {
  const card = document.getElementById("last-guess");
  if (!feedback) {
    card.style.display = "none"; // hide card if no feedback yet
    return;
  }
  card.style.display = "block"; // show card when feedback exists
  document.getElementById("last-guess-array").textContent = formatGuessArray(
    feedback.guess
  );
  document.getElementById(
    "pill-numbers"
  ).textContent = `# Numbers: ${feedback.correct_numbers}`;
  document.getElementById(
    "pill-positions"
  ).textContent = `# Positions: ${feedback.correct_positions}`;
  document.getElementById("last-guess-message").textContent =
    feedback.message || "";
}

/* ---------- renderers ---------- */

// Render the header info (game id, attempts, status, difficulty)
function renderGameHeader(state) {
  const info = document.getElementById("game-info");
  info.innerHTML =
    `<span class="badge">Game ID: <b>${state.game_id || "none"}</b></span>` +
    `<span class="badge">Attempts: ${state.attempts_left}</span>` +
    `<span class="badge">Status: ${state.status}</span>` +
    `<span class="badge">Difficulty: ${state.difficulty || difficulty}</span>`;

  // Show instructions depending on difficulty
  const help = document.getElementById("guess-help");
  const gi = document.getElementById("guess-input");
  if ((state.difficulty || difficulty) === "easy") {
    help.textContent = "Enter 3 digits (0–7). Example: 0 1 2";
    gi.placeholder = "0 1 2";
  } else if ((state.difficulty || difficulty) === "hard") {
    help.textContent = "Enter 5 digits (0–7). Example: 0 1 2 3 4";
    gi.placeholder = "0 1 2 3 4";
  } else {
    help.textContent = "Enter 4 digits (0–7). Example: 0 1 2 3";
    gi.placeholder = "0 1 2 3";
  }

  // Disable guess + hint buttons if game is over
  const hasGame = Boolean(state.game_id);
  document.getElementById("guess-btn").disabled =
    !hasGame || state.status !== "in_progress";
  document.getElementById("hint-btn").disabled =
    !hasGame || state.status !== "in_progress";
}

// Render the entire history table of guesses
function renderHistory(history) {
  const body = document.getElementById("history-body");
  body.innerHTML = ""; // clear first
  let idx = 0;
  while (idx < history.length) {
    const h = history[idx];
    const tr = document.createElement("tr");

    // Column # (guess number)
    const c1 = document.createElement("td");
    c1.textContent = (idx + 1).toString();

    // Column guess itself
    const c2 = document.createElement("td");
    c2.className = "mono nowrap"; // style: monospace + no wrap
    c2.textContent = formatGuessArray(h.guess);

    // Correct numbers + positions
    const c3 = document.createElement("td");
    c3.textContent = h.correct_numbers.toString();
    const c4 = document.createElement("td");
    c4.textContent = h.correct_positions.toString();

    // Message from backend (ex. "2 correct number(s) and 1 correct location(s)")
    const c5 = document.createElement("td");
    c5.textContent = h.message || "";

    tr.appendChild(c1);
    tr.appendChild(c2);
    tr.appendChild(c3);
    tr.appendChild(c4);
    tr.appendChild(c5);
    body.appendChild(tr);

    idx = idx + 1;
  }
}

/* ---------- API calls ---------- */

// Pull latest state of the game from backend
async function refreshState() {
  if (!gameId) return;

  const url = `${API_BASE}/games/${gameId}`;
  const resp = await fetch(url, { headers: { accept: "application/json" } });
  if (!resp.ok) return;

  const state = await resp.json();
  renderGameHeader(state);
  renderHistory(state.history);

  // Clear any old hint line
  document.getElementById("hint-result").textContent = "";

  // If game ended, disable buttons
  if (state.status !== "in_progress") {
    document.getElementById("guess-btn").disabled = true;
    document.getElementById("hint-btn").disabled = true;
  }
}

// Start a new game with the selected difficulty
async function startGame() {
  const dropdown = document.getElementById("difficulty");
  difficulty = dropdown.value;

  const url = `${API_BASE}/games?difficulty=${encodeURIComponent(difficulty)}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { accept: "application/json" },
  });
  if (!resp.ok) {
    alert("Failed to start game.");
    return;
  }

  const data = await resp.json();
  gameId = data.game_id;

  // Reset UI panels
  clearError(); // hide any previous error
  document.getElementById("last-feedback").textContent = "";
  document.getElementById("final-note").textContent = "";
  document.getElementById("secret-box").textContent = "";
  document.getElementById("guess-input").value = "";
  setLastGuessCard(null);

  renderGameHeader(data);
  await refreshState();
}

// Submit a guess to backend and update UI
async function submitGuess() {
  if (!gameId) {
    alert("Please start a game first.");
    return;
  }

  const input = document.getElementById("guess-input");
  const guessArray = parseGuess(input.value);

  const resp = await fetch(`${API_BASE}/games/${gameId}/guess`, {
    method: "POST",
    headers: { "Content-Type": "application/json", accept: "application/json" },
    body: JSON.stringify({ guess: guessArray }),
  });

  if (!resp.ok) {
    // backend returns error if wrong length guess etc.
    const clone = resp.clone();
    let msg = "Invalid input.";
    try {
      const data = await resp.json();
      if (data && data.detail) {
        if (Array.isArray(data.detail)) {
          msg = data.detail
            .map((d) => d.msg || d.detail || "Invalid input.")
            .join("; ");
        } else if (typeof data.detail === "string") {
          msg = data.detail;
        }
      }
    } catch {
      // If JSON parse fails, fall back to raw text from the clone
      const text = await clone.text();
      msg = text || msg;
    }
    setError(`⚠️ ${msg}`);
    setLastGuessCard(null);
    return;
  }

  const result = await resp.json();

  // Successful guess -> hide any previous error
  clearError();

  // Update "Last Guess" card
  if (result && result.feedback) {
    setLastGuessCard(result.feedback);
  } else {
    setLastGuessCard(null);
  }

  // If game is finished, show secret + note
  if (result.status !== "in_progress") {
    if (result.secret) {
      document.getElementById(
        "secret-box"
      ).innerHTML = `Secret: <span class="secret">${formatGuessArray(
        result.secret
      )}</span>`;
    }
    if (result.note) {
      document.getElementById("final-note").textContent = result.note;
    }
    document.getElementById("guess-btn").disabled = true;
    document.getElementById("hint-btn").disabled = true;
  } else {
    document.getElementById("final-note").textContent = "";
  }

  await refreshState();
}

// Request a hint from backend (only once per game)
async function getHint() {
  if (!gameId) {
    alert("Start a game first.");
    return;
  }

  const resp = await fetch(`${API_BASE}/games/${gameId}/hint`, {
    method: "GET",
    headers: { accept: "application/json" },
  });

  if (resp.status === 409) {
    // Backend tells us: already used or game finished
    const text = await resp.text();
    document.getElementById("hint-result").textContent = text;
    return;
  }
  if (!resp.ok) {
    const text = await resp.text();
    document.getElementById("hint-result").textContent = `Hint failed: ${text}`;
    return;
  }

  const data = await resp.json();
  const pos = data.position;
  const digit = data.digit;
  const note = data.note ? ` — ${data.note}` : "";
  document.getElementById(
    "hint-result"
  ).textContent = `Hint: Position at index ${pos} is ${digit}${note}`;

  // Disable hint button (only once per game)
  document.getElementById("hint-btn").disabled = true;
}

// Load stats and render as pretty table
async function refreshStats() {
  const resp = await fetch(`${API_BASE}/stats`, {
    headers: { accept: "application/json" },
  });
  if (!resp.ok) {
    document.getElementById("stats-msg").textContent = "Failed to load stats.";
    return;
  }
  const data = await resp.json();
  document.getElementById("stats-msg").textContent = "Stats refreshed.";

  const statsBox = document.getElementById("stats-json");
  const avg = data.average_guesses_to_win ?? "–";
  const fastest = data.fastest_win_attempts ?? "–";

  // Instead of raw JSON, render a table grouped by sections
  statsBox.innerHTML = `
    <table class="table stats-table">
      <thead><tr><th colspan="2" class="section-head">🌸 Overall</th></tr></thead>
      <tbody>
        <tr><td>Games Started</td><td>${data.games_started}</td></tr>
        <tr><td>Games Won</td><td>${data.games_won}</td></tr>
        <tr><td>Games Lost</td><td>${data.games_lost}</td></tr>
      </tbody>

      <thead><tr><th colspan="2" class="section-head">🔥 Streaks</th></tr></thead>
      <tbody>
        <tr><td>Current Streak</td><td>${data.current_streak}</td></tr>
        <tr><td>Best Streak</td><td>${data.best_streak}</td></tr>
      </tbody>

      <thead><tr><th colspan="2" class="section-head">⭐ Performance</th></tr></thead>
      <tbody>
        <tr><td>Average Guesses to Win</td><td>${avg}</td></tr>
        <tr><td>Fastest Win Attempts</td><td>${fastest}</td></tr>
      </tbody>

      <thead><tr><th colspan="2" class="section-head">🎯 By Difficulty</th></tr></thead>
      <tbody>
        <tr><td>Easy Games Started</td><td>${data.easy_started}</td></tr>
        <tr><td>Medium Games Started</td><td>${data.medium_started}</td></tr>
        <tr><td>Hard Games Started</td><td>${data.hard_started}</td></tr>
        <tr><td>Easy Wins</td><td>${data.easy_won}</td></tr>
        <tr><td>Medium Wins</td><td>${data.medium_won}</td></tr>
        <tr><td>Hard Wins</td><td>${data.hard_won}</td></tr>
      </tbody>
    </table>
  `;
}

// Reset stats endpoint
async function resetStats() {
  const resp = await fetch(`${API_BASE}/stats/reset`, {
    method: "POST",
  });
  if (!resp.ok) {
    document.getElementById("stats-msg").textContent = "Failed to reset stats.";
    return;
  }
  document.getElementById("stats-msg").textContent = "Stats reset.";
  document.getElementById("stats-json").textContent = "";
}

/* ---------- wire up ---------- */

// Attach all button click handlers after DOM is ready
window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("start-btn").addEventListener("click", startGame);
  document.getElementById("guess-btn").addEventListener("click", submitGuess);
  document.getElementById("hint-btn").addEventListener("click", getHint);
  document
    .getElementById("refresh-stats")
    .addEventListener("click", refreshStats);
  document.getElementById("reset-stats").addEventListener("click", resetStats);
  // Clear error as the user edits their guess
  const gi = document.getElementById("guess-input");
  gi.addEventListener("input", clearError);
});
