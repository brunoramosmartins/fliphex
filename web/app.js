/* FLIPHEX in the browser.
 *
 * This file draws and nothing else. Every legality question, every flip and
 * every score comes back from `ui/web_bridge.py` running under Pyodide, per
 * adr-013 clause 2: the rules are the engine that produced the project's exact
 * solutions, not a second implementation that could disagree with it.
 *
 * The one piece of geometry here is the hexagon's own outline. Cell *positions*
 * come from `ui.web_bridge.layout`, which is checked against `Board.neighbour`
 * by test — so a cell drawn in the wrong place is a test failure rather than a
 * picture that looks slightly off.
 */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const SVG_NS = "http://www.w3.org/2000/svg";

/* Where the engine is unpacked inside the WebAssembly filesystem. */
const PY_ROOT = "/app";

/* Flat-top hexagons: vertices every 60 degrees starting at due East, so the
 * flat edges land on top and bottom and the points on left and right. */
const VERTEX_ANGLES = [0, 60, 120, 180, 240, 300];

/* Direction d, clockwise from North, points at angle -90 + 60d degrees. The
 * same six offsets `tests/test_web_bridge.py` asserts the layout against. */
const directionAngle = (d) => (-90 + 60 * d) * (Math.PI / 180);

const $ = (id) => document.getElementById(id);

const ui = {
  boot: $("boot"),
  bootText: $("boot-text"),
  board: $("board"),
  badge: $("engine-badge"),
  scoreline: $("scoreline"),
  scorePurple: $("score-purple"),
  scoreGreen: $("score-green"),
  turn: $("turn"),
  commentary: $("commentary"),
  hand: $("hand"),
  handTitle: $("hand-title"),
  hint: $("hint"),
  rotationPanel: $("rotation-panel"),
  rotations: $("rotations"),
  undo: $("undo"),
  cancel: $("cancel"),
  newGame: $("new-game"),
  variant: $("variant"),
  opponent: $("opponent"),
};

/* Everything mutable, in one place. */
const state = {
  py: null,
  game: null,
  geometry: null,
  snapshot: null,
  centres: new Map(),
  selectedTile: null,
  selectedCell: null,
  busy: false,
};

/* -- hexagon geometry ------------------------------------------------------ */

function hexPoints(cx, cy, r) {
  return VERTEX_ANGLES
    .map((deg) => {
      const a = (deg * Math.PI) / 180;
      return `${(cx + r * Math.cos(a)).toFixed(4)},${(cy + r * Math.sin(a)).toFixed(4)}`;
    })
    .join(" ");
}

function el(name, attrs = {}, parent = null) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

/* One arrow, drawn from just outside the centre to just inside the edge. */
function drawArrow(parent, cx, cy, direction, className, headClass) {
  const a = directionAngle(direction);
  const [dx, dy] = [Math.cos(a), Math.sin(a)];
  const from = 0.22;
  const to = 0.66;
  el("line", {
    x1: cx + dx * from,
    y1: cy + dy * from,
    x2: cx + dx * to,
    y2: cy + dy * to,
    "stroke-width": 0.06,
    class: `arrow ${className}`,
  }, parent);
  const tip = 0.82;
  const wing = 0.13;
  const [px, py] = [-dy, dx];
  el("polygon", {
    points: [
      `${cx + dx * tip},${cy + dy * tip}`,
      `${cx + dx * to + px * wing},${cy + dy * to + py * wing}`,
      `${cx + dx * to - px * wing},${cy + dy * to - py * wing}`,
    ].join(" "),
    class: `arrow-head ${headClass}`,
  }, parent);
}

/* A standalone tile glyph, for the hand and the rotation strip. */
function tileGlyph(arrows, colour) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "-1.15 -1.15 2.3 2.3");
  svg.setAttribute("aria-hidden", "true");
  el("polygon", {
    points: hexPoints(0, 0, 1),
    fill: colour === "GREEN" ? "var(--green)" : "var(--purple)",
  }, svg);
  for (const d of arrows) {
    drawArrow(svg, 0, 0, d, "arrow-placed", "arrow-placed-head");
  }
  if (arrows.length === 0) {
    el("circle", { cx: 0, cy: 0, r: 0.18, fill: "rgba(255,255,255,.7)" }, svg);
  }
  return svg;
}

/* -- board ----------------------------------------------------------------- */

function drawBoard(geometry) {
  const svg = ui.board;
  svg.textContent = "";
  state.centres.clear();

  const xs = geometry.cells.map((c) => c.x);
  const ys = geometry.cells.map((c) => c.y);
  const pad = 1.15;
  svg.setAttribute(
    "viewBox",
    [
      Math.min(...xs) - pad,
      Math.min(...ys) - pad,
      Math.max(...xs) - Math.min(...xs) + 2 * pad,
      Math.max(...ys) - Math.min(...ys) + 2 * pad,
    ].join(" "),
  );

  const overlay = el("g", { id: "overlay" });
  for (const cell of geometry.cells) {
    state.centres.set(cell.id, cell);
    const g = el("g", { class: "cell-group", "data-cell": cell.id }, svg);
    el("polygon", {
      points: hexPoints(cell.x, cell.y, 0.94),
      class: "cell cell-empty",
      "data-role": "fill",
    }, g);
    el("polygon", { points: hexPoints(cell.x, cell.y, 0.94), class: "cell-outline" }, g);
    el("g", { "data-role": "arrows" }, g);
    const label = el("text", {
      x: cell.x,
      y: cell.y,
      class: "cell-name",
      "data-role": "name",
    }, g);
    label.textContent = cell.name;
    el("circle", { cx: cell.x, cy: cell.y, r: 0.16, class: "playable-mark", opacity: 0 }, g);
    el("polygon", { points: hexPoints(cell.x, cell.y, 0.94), class: "ring" }, g);
    const hit = el("polygon", {
      points: hexPoints(cell.x, cell.y, 0.94),
      class: "cell-hit",
      "data-role": "hit",
    }, g);
    hit.addEventListener("click", () => onCellClick(cell.id));
  }
  svg.appendChild(overlay);
  svg.hidden = false;
  ui.boot.hidden = true;
  ui.scoreline.hidden = false;
}

function paintBoard(snapshot) {
  for (const [id] of state.centres) {
    const group = ui.board.querySelector(`g[data-cell="${id}"]`);
    const fill = group.querySelector('[data-role="fill"]');
    const colour = snapshot.colours[id];
    fill.setAttribute(
      "class",
      `cell ${colour === "EMPTY" ? "cell-empty" : colour === "PURPLE" ? "cell-purple" : "cell-green"}`,
    );
    group.querySelector('[data-role="name"]').setAttribute(
      "fill",
      colour === "EMPTY" ? "var(--ink-soft)" : "rgba(255,255,255,.72)",
    );
  }
}

/* Arrows of every tile already on the board, redrawn from the move history the
 * bridge reports. Placed tiles are inert (adr-003) — these are a record of what
 * fired, not something that can fire again. */
function paintArrows(placed) {
  for (const [id] of state.centres) {
    ui.board.querySelector(`g[data-cell="${id}"] [data-role="arrows"]`).textContent = "";
  }
  for (const item of placed) {
    const cell = state.centres.get(item.cell);
    const host = ui.board.querySelector(`g[data-cell="${item.cell}"] [data-role="arrows"]`);
    for (const d of item.arrows) {
      drawArrow(host, cell.x, cell.y, d, "arrow-placed", "arrow-placed-head");
    }
  }
}

function clearOverlay() {
  ui.board.querySelector("#overlay").textContent = "";
}

/* What a rotation would do, drawn on the board itself rather than described. */
function previewRotation(option) {
  const overlay = ui.board.querySelector("#overlay");
  overlay.textContent = "";
  const cell = state.centres.get(state.selectedCell);
  const colour = state.snapshot.to_move === "GREEN" ? "var(--green)" : "var(--purple)";
  el("polygon", {
    points: hexPoints(cell.x, cell.y, 0.94),
    fill: colour,
    class: "preview-tile",
  }, overlay);
  for (const d of option.arrows) {
    drawArrow(overlay, cell.x, cell.y, d, "preview-arrow", "preview-arrow-head");
  }
  for (const effect of option.effects) {
    if (effect.target === null) continue;
    const target = state.centres.get(effect.target);
    if (effect.kind === "flip" || effect.kind === "self-flip") {
      el("polygon", {
        points: hexPoints(target.x, target.y, 0.82),
        class: effect.kind === "flip" ? "preview-target-flip" : "preview-target-self",
      }, overlay);
    }
  }
}

function markPlayable(cells) {
  for (const [id] of state.centres) {
    const group = ui.board.querySelector(`g[data-cell="${id}"]`);
    const playable = cells.includes(id);
    group.classList.toggle("playable", playable);
    group.querySelector('[data-role="hit"]').classList.toggle("playable", playable);
    group.querySelector(".playable-mark").setAttribute("opacity", playable ? 1 : 0);
  }
}

function clearMarks() {
  for (const [id] of state.centres) {
    const group = ui.board.querySelector(`g[data-cell="${id}"]`);
    group.classList.remove("playable", "selected");
    group.querySelector('[data-role="hit"]').classList.remove("playable");
    group.querySelector(".playable-mark").setAttribute("opacity", 0);
  }
}

function animateFlips(cells) {
  for (const id of cells) {
    const fill = ui.board.querySelector(`g[data-cell="${id}"] [data-role="fill"]`);
    fill.classList.remove("just-flipped");
    void fill.getBoundingClientRect();
    fill.classList.add("just-flipped");
  }
}

/* -- panels ---------------------------------------------------------------- */

function renderHand() {
  const snapshot = state.snapshot;
  // Called from `resetSelection`, which runs at times when no game exists yet.
  // Returning is right; reading through a null snapshot is how the first
  // version of this page failed to boot at all.
  if (!snapshot) return;
  const mover = snapshot.to_move;
  const hand = snapshot.hands[mover];
  ui.handTitle.textContent = `${mover === "PURPLE" ? "Purple" : "Green"} — ${hand.length} left`;
  ui.hand.textContent = "";

  const interactive = !snapshot.terminal && isHumanTurn();
  for (const piece of hand) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "piece";
    button.disabled = !interactive;
    button.setAttribute("aria-pressed", String(state.selectedTile === piece.tile));
    button.title = `${piece.archetype} — ${piece.arrows.length} arrow(s), ${piece.rotations.length} distinct rotation(s)`;
    button.appendChild(tileGlyph(piece.arrows, mover));
    const name = document.createElement("span");
    name.textContent = piece.archetype;
    button.appendChild(name);
    button.addEventListener("click", () => onTileClick(piece.tile));
    ui.hand.appendChild(button);
  }
}

function renderRotations(options) {
  ui.rotations.textContent = "";
  for (const option of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rot";
    button.appendChild(tileGlyph(option.arrows, state.snapshot.to_move));
    const net = document.createElement("span");
    const sign = option.net > 0 ? "up" : option.net < 0 ? "down" : "flat";
    net.className = `net ${sign}`;
    net.textContent = option.net > 0 ? `+${option.net}` : String(option.net);
    button.appendChild(net);
    button.addEventListener("mouseenter", () => previewRotation(option));
    button.addEventListener("focus", () => previewRotation(option));
    button.addEventListener("click", () => playMove(option.rotation));
    ui.rotations.appendChild(button);
  }
  ui.rotationPanel.hidden = options.length === 0;
}

function say(html) {
  ui.commentary.innerHTML = html;
}

function describe(result) {
  const flips = result.effects.filter((e) => e.kind === "flip").length;
  const selfs = result.effects.filter((e) => e.kind === "self-flip").length;
  const who = result.placed_as === "PURPLE" ? "Purple" : "Green";
  const cell = state.centres.get(result.move.cell).name;
  const parts = [`<b>${who}</b> played <b>${result.archetype}</b> on <b>${cell}</b>`];
  if (flips) parts.push(`flipping ${flips}`);
  if (selfs) parts.push(`<span class="bad">handing back ${selfs}</span>`);
  if (!flips && !selfs) parts.push("with nothing to flip");
  return `${parts.join(", ")}.`;
}

function refresh(snapshot) {
  state.snapshot = snapshot;
  paintBoard(snapshot);
  ui.scorePurple.textContent = snapshot.score.PURPLE;
  ui.scoreGreen.textContent = snapshot.score.GREEN;
  ui.undo.disabled = !snapshot.can_undo || state.busy;

  if (snapshot.terminal) {
    ui.turn.textContent = `${snapshot.winner === "PURPLE" ? "Purple" : "Green"} wins`;
    ui.turn.classList.add("win");
    ui.hint.textContent = "The board is full. 25 is odd, so there is never a draw.";
  } else {
    ui.turn.classList.remove("win");
    ui.turn.textContent = `${snapshot.to_move === "PURPLE" ? "Purple" : "Green"} to move`;
    ui.hint.textContent = isHumanTurn()
      ? "Pick a piece, then a cell."
      : "The agent is thinking…";
  }
  renderHand();
}

/* -- interaction ----------------------------------------------------------- */

function isHumanTurn() {
  if (ui.opponent.value === "human") return true;
  return state.snapshot.to_move === "PURPLE";
}

function resetSelection() {
  state.selectedTile = null;
  state.selectedCell = null;
  clearMarks();
  clearOverlay();
  ui.rotationPanel.hidden = true;
  renderHand();
}

function onTileClick(tile) {
  if (state.busy || state.snapshot.terminal || !isHumanTurn()) return;
  if (state.selectedTile === tile) return resetSelection();
  state.selectedTile = tile;
  state.selectedCell = null;
  clearOverlay();
  ui.rotationPanel.hidden = true;
  markPlayable(state.game.playable_cells(tile).toJs());
  renderHand();
  ui.hint.textContent = "Now pick a highlighted cell.";
}

function onCellClick(cell) {
  if (state.busy || state.selectedTile === null) return;
  const group = ui.board.querySelector(`g[data-cell="${cell}"]`);
  if (!group.classList.contains("playable")) return;
  for (const [id] of state.centres) {
    ui.board.querySelector(`g[data-cell="${id}"]`).classList.toggle("selected", id === cell);
  }
  state.selectedCell = cell;
  const options = state.game.options(cell, state.selectedTile).toJs({ dict_converter: Object.fromEntries });
  renderRotations(options);
  if (options.length) previewRotation(options[0]);
  ui.hint.textContent = "Choose a rotation.";
}

async function playMove(rotation) {
  if (state.busy) return;
  const result = state.game
    .play(state.selectedCell, state.selectedTile, rotation)
    .toJs({ dict_converter: Object.fromEntries });
  resetSelection();
  refresh(result.snapshot);
  paintArrows(placedTiles());
  animateFlips(result.flipped);
  say(describe(result));
  await maybeAgentMove();
}

function placedTiles() {
  return state.game.history_for_drawing().toJs({ dict_converter: Object.fromEntries });
}

async function maybeAgentMove() {
  if (state.snapshot.terminal || isHumanTurn()) return;
  state.busy = true;
  ui.undo.disabled = true;
  // Yield once so the human's move paints before the agent's search blocks.
  await new Promise((resolve) => setTimeout(resolve, 60));
  try {
    const result = state.game
      .agent_move_by_name(ui.opponent.value)
      .toJs({ dict_converter: Object.fromEntries });
    refresh(result.snapshot);
    paintArrows(placedTiles());
    animateFlips(result.flipped);
    say(`${describe(result)}`);
  } finally {
    state.busy = false;
    ui.undo.disabled = !state.snapshot.can_undo;
  }
}

function onUndo() {
  if (state.busy) return;
  // Two plies when an agent holds a seat, so the human gets their turn back.
  state.game.undo();
  if (ui.opponent.value !== "human") state.game.undo();
  resetSelection();
  refresh(state.game.snapshot().toJs({ dict_converter: Object.fromEntries }));
  paintArrows(placedTiles());
  say("");
}

async function startGame() {
  const conv = { dict_converter: Object.fromEntries };
  const [cols, rows] = ui.variant.value.split("x").map(Number);
  state.game = state.py.globals.get("new_game")(cols, rows);
  state.geometry = state.game.geometry().toJs(conv);

  // Order matters, and it caught this page out once. `resetSelection` renders
  // the hand, and rendering the hand reads `state.snapshot` — which is null
  // until the first `refresh`. The snapshot is therefore taken and installed
  // before anything that might read it.
  state.snapshot = state.game.snapshot().toJs(conv);
  state.selectedTile = null;
  state.selectedCell = null;
  state.busy = false;

  drawBoard(state.geometry);
  refresh(state.snapshot);
  paintArrows([]);
  clearOverlay();
  clearMarks();
  ui.rotationPanel.hidden = true;
  say("");
}

/* -- boot ------------------------------------------------------------------ */

async function boot() {
  try {
    ui.bootText.textContent = "Downloading the Python runtime…";
    const { loadPyodide } = await import(`${PYODIDE}pyodide.mjs`);
    const py = await loadPyodide({ indexURL: PYODIDE });

    ui.bootText.textContent = "Unpacking the engine…";
    const payload = await (await fetch("payload.json")).json();
    // Absolute paths: Emscripten's working directory is not the filesystem
    // root, and a relative mkdirTree fails with a bare ENOENT that says
    // nothing about which path it meant.
    for (const [path, source] of Object.entries(payload)) {
      const full = `${PY_ROOT}/${path}`;
      py.FS.mkdirTree(full.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(full, source);
    }

    // No Python is defined here. Everything the page calls lives in
    // `ui/web_bridge.py`, where the test suite can reach it — a rule the page
    // broke once already by carrying its own subclass in this string.
    ui.bootText.textContent = "Starting the rules…";
    await py.runPythonAsync(`
import sys
sys.path.insert(0, ${JSON.stringify(PY_ROOT)})
from ui.web_bridge import WebGame
new_game = WebGame
`);

    state.py = py;
    ui.badge.textContent = "ready";
    ui.badge.classList.add("ready");
    ui.newGame.disabled = false;
    await startGame();
  } catch (error) {
    ui.badge.textContent = "failed";
    ui.badge.classList.add("failed");
    ui.bootText.textContent = "The engine did not start.";
    const note = ui.boot.querySelector(".boot-note");
    note.textContent = String(error).slice(0, 300);
    console.error(error);
  }
}

ui.newGame.addEventListener("click", startGame);
ui.variant.addEventListener("change", () => { if (state.py) startGame(); });
ui.opponent.addEventListener("change", () => { if (state.py) startGame(); });
ui.undo.addEventListener("click", onUndo);
ui.cancel.addEventListener("click", resetSelection);

boot();
