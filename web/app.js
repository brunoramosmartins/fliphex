/* FLIPHEX in the browser.
 *
 * This file draws and nothing else. Every legality question, every flip and
 * every score comes back from `ui/session.py` running under Pyodide, per
 * adr-013 clause 2: the rules are the engine that produced the project's exact
 * solutions, not a second implementation that could disagree with it.
 *
 * The one piece of geometry here is the hexagon's own outline. Cell *positions*
 * come from `ui.session.layout`, which is checked against `Board.neighbour`
 * by test — so a cell drawn in the wrong place is a test failure rather than a
 * picture that looks slightly off.
 */

/* The CDN, unless something overrides it before this module loads. The
 * override exists for `web/test/page.test.mjs`, which points it at a local
 * pyodide package so the suite needs no network — and so that the test can
 * import this file *unmodified*. A test that rewrites its subject is testing
 * something else. */
const PYODIDE =
  globalThis.FLIPHEX_PYODIDE_URL ?? "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const SVG_NS = "http://www.w3.org/2000/svg";

/* Where the engine is unpacked inside the WebAssembly filesystem. */
const PY_ROOT = "/app";

/* -- which seats this page may offer --------------------------------------- */

/* adr-013's second amendment withdrew every agent above the heuristic from the
 * *deployed* page, and said in the same breath that "`ui/seats.py` builds all
 * six and the local page serves them". It did not. One `index.html` served both
 * origins, so "deployed" and "local" were the same list and that sentence was
 * aspirational — the solver was reachable only from the pygame window.
 *
 * The split is enforced here, and it **fails closed**: a host this file does
 * not recognise as local gets the published list. That way a new deployment
 * target — a custom domain, a preview URL, somebody else's fork — is restricted
 * by default rather than by remembering to add it.
 */
const PUBLISHED_SEATS = ["human", "heuristic"];
const LOCAL_SEATS = ["human", "random", "heuristic", "solver"];

/* `uct` and `az` are in `SEAT_KINDS` and are deliberately in neither list:
 * `agents/az_agent.py` is excluded from the payload by `scripts/build_web.py`
 * because it imports torch, which has no WebAssembly build. They are not
 * withheld from the browser — they cannot run in one. */
const SEAT_LABELS = {
  human: "a second player",
  random: "the random agent",
  heuristic: "the heuristic agent",
  solver: "the exact solver",
};

function isLocalHost(hostname) {
  const host = String(hostname ?? "").toLowerCase().replace(/^\[|\]$/g, "");
  // Empty is `file://`, which has no host at all and is as local as it gets.
  if (host === "" || host === "localhost" || host.endsWith(".localhost")) return true;
  if (host === "::1") return true;
  // `.local` is reserved for mDNS and never resolves on the public internet.
  // It is how a phone reaches a laptop on the same wifi.
  if (host.endsWith(".local")) return true;
  const quads = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!quads) return false;
  const [a, b] = quads.slice(1, 5).map(Number);
  if (quads.slice(1, 5).some((q) => Number(q) > 255)) return false;
  // Loopback and the three RFC 1918 private ranges. A LAN address is how the
  // page is reached from a phone on the same wifi, and that is still a local
  // checkout being served by its own author.
  return a === 127 || a === 10 || (a === 192 && b === 168) || (a === 172 && b >= 16 && b <= 31);
}

function seatsFor(hostname) {
  return isLocalHost(hostname) ? LOCAL_SEATS : PUBLISHED_SEATS;
}

/* Seats whose search blocks the only thread the page has.
 *
 * Pyodide runs on the main thread, so a 3x3 exhaustive solve does not merely
 * take a while — it freezes the tab: no spinner turns, no click registers. The
 * page therefore *names* the freeze before entering it rather than animating
 * something that will visibly stall, which is the one thing that makes a long
 * wait look like a crash. */
const BLOCKING_SEATS = new Set(["solver"]);

/* Flat-top hexagons: vertices every 60 degrees starting at due East, so the
 * flat edges land on top and bottom and the points on left and right. */
const VERTEX_ANGLES = [0, 60, 120, 180, 240, 300];

/* Direction d, clockwise from North, points at angle -90 + 60d degrees. The
 * same six offsets `tests/test_session.py` asserts the layout against. */
const directionAngle = (d) => (-90 + 60 * d) * (Math.PI / 180);

const $ = (id) => document.getElementById(id);

const ui = {
  boot: $("boot"),
  boardWrap: $("board-wrap"),
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
  side: $("side"),
  opponent: $("opponent"),
  originNote: $("origin-note"),
};

/* Replace the opponent list with the one this origin is allowed. `index.html`
 * ships the published pair as the pre-script fallback; this widens it on a
 * local checkout and never narrows below it. */
function fillSeats(hostname) {
  const seats = seatsFor(hostname);
  const keep = ui.opponent.value;
  ui.opponent.textContent = "";
  for (const seat of seats) {
    const option = document.createElement("option");
    option.value = seat;
    option.textContent = SEAT_LABELS[seat];
    ui.opponent.appendChild(option);
  }
  ui.opponent.value = seats.includes(keep) ? keep : "heuristic";
  if (ui.originNote) {
    ui.originNote.textContent = seats.includes("solver")
      ? "Local checkout — the exact solver is offered here, not on the published page."
      : "";
  }
  return seats;
}

/* Let the browser paint before something blocks it.
 *
 * Two frames and then a task: one `requestAnimationFrame` schedules work
 * *before* the next paint, so a single one would still block on the frame it
 * was meant to let through. */
function nextPaint() {
  return new Promise((resolve) => {
    const raf = globalThis.requestAnimationFrame ?? window?.requestAnimationFrame;
    if (typeof raf === "function") {
      raf(() => raf(() => setTimeout(resolve, 0)));
    } else {
      setTimeout(resolve, 60);
    }
  });
}

/* Everything mutable, in one place. */
const state = {
  py: null,
  game: null,
  geometry: null,
  snapshot: null,
  centres: new Map(),
  selectedTile: null,
  selectedCell: null,
  armedRotation: null,
  busy: false,
};

/* -- instrumentation (EXP-019) --------------------------------------------- */

/* The page times itself, because a stopwatch cannot separate these four and an
 * impression is not a measurement. Marks are cumulative from navigation start;
 * both totals and deltas are reported, since a reader who sees only deltas
 * cannot tell a slow runtime from a slow import. */
const MARK_ORDER = ["chrome", "board", "runtime", "engine", "playable"];
const marks = new Map();

function mark(name) {
  marks.set(name, performance.now());
}

function reportMarks() {
  const rows = [];
  let previous = 0;
  for (const name of MARK_ORDER) {
    if (!marks.has(name)) continue;
    const total = marks.get(name);
    rows.push({ mark: name, deltaMs: Math.round(total - previous), totalMs: Math.round(total) });
    previous = total;
  }
  // Exposed so a measurement run can read it without scraping the console.
  window.fliphexMarks = rows;
  console.table(rows);

  const playable = marks.get("playable");
  if (playable !== undefined) {
    ui.badge.textContent = `ready in ${(playable / 1000).toFixed(2)}s`;
    ui.badge.title = rows.map((r) => `${r.mark} +${r.deltaMs}ms`).join("  ");
  }
  recordRun(rows);
  return rows;
}

/* Bytes actually pulled over the network this load.
 *
 * A resource served from cache reports `transferSize` 0, so this separates a
 * cold load from a warm one by **measuring** it rather than by trusting whoever
 * was clicking to remember which they just did. EXP-019's falsifier says that
 * if the two conditions do not differ, its rules are not applied — and that
 * cannot be checked from a number that was assumed. */
function transferredBytes() {
  try {
    return performance
      .getEntriesByType("resource")
      .reduce((total, entry) => total + (entry.transferSize || 0), 0);
  } catch {
    return null;
  }
}

const RUNS_KEY = "fliphex.exp019.runs";

/* Per-viewer convenience only: this survives a reload so ten loads can be
 * collected without transcribing ten tables by hand. It is not the record —
 * `fliphexReport()` prints what goes into the registry. Every access is
 * guarded, because storage throws in a private window and comes back empty
 * after a site-data clear. */
function readRuns() {
  try {
    return JSON.parse(localStorage.getItem(RUNS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function recordRun(rows) {
  const bytes = transferredBytes();
  const run = {
    at: new Date().toISOString(),
    playableMs: rows.at(-1)?.totalMs ?? null,
    marks: Object.fromEntries(rows.map((r) => [r.mark, r.deltaMs])),
    transferredBytes: bytes,
    // 1 MB is far above a warm load's stray bytes and far below the runtime's
    // 14 MB, so nothing lands near the line.
    cache: bytes === null ? "unknown" : bytes > 1_000_000 ? "cold" : "warm",
    ua: globalThis.navigator?.userAgent ?? "unknown",
  };
  try {
    localStorage.setItem(RUNS_KEY, JSON.stringify([...readRuns(), run]));
  } catch {
    /* no storage: the run is still in fliphexMarks for this page */
  }
  window.fliphexRun = run;
  console.log(
    `  EXP-019  ${run.cache}  playable ${run.playableMs} ms  ` +
      `(${((bytes ?? 0) / 1e6).toFixed(1)} MB transferred)  — ` +
      `${readRuns().length} run(s) collected, fliphexReport() to print`,
  );
}

/* Print every collected load, grouped by cache state. Copy the JSON into the
 * registry: cells are reported whole, and no load is dropped for looking
 * wrong. */
function fliphexReport() {
  const runs = readRuns();
  if (!runs.length) {
    console.log("no runs collected — reload the page at least once");
    return [];
  }
  console.table(
    runs.map((r, i) => ({
      "#": i + 1,
      cache: r.cache,
      playableMs: r.playableMs,
      chrome: r.marks.chrome,
      runtime: r.marks.runtime,
      engine: r.marks.engine,
      playable: r.marks.playable,
      MB: ((r.transferredBytes ?? 0) / 1e6).toFixed(1),
    })),
  );
  for (const state of ["cold", "warm"]) {
    const cell = runs.filter((r) => r.cache === state).map((r) => r.playableMs);
    if (cell.length) {
      console.log(
        `  ${state}: n=${cell.length}  playable ms = ${cell.join(", ")}` +
          `  (min ${Math.min(...cell)}, max ${Math.max(...cell)})`,
      );
    }
  }
  console.log(JSON.stringify(runs, null, 1));
  return runs;
}

function fliphexReset() {
  try {
    localStorage.removeItem(RUNS_KEY);
  } catch {
    /* nothing to clear */
  }
  console.log("collected runs cleared");
}

/* Timed around the one SolverAgent call, per EXP-019's third rule. Exposed on
 * `window` rather than wired to a control: it is a measurement, not a feature,
 * and it is expensive enough that nobody should trigger it by accident. */
async function timeSolverOpening(cols = 3, rows = 3) {
  const conv = { dict_converter: Object.fromEntries };
  const probe = state.py.globals.get("new_game")(cols, rows);
  const started = performance.now();
  probe.agent_move_by_name("solver");
  const elapsed = Math.round(performance.now() - started);
  probe.destroy();
  console.log(`solver opening on ${cols}x${rows}: ${elapsed} ms`);
  return elapsed;
}

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

/* One arrow, drawn from just outside the centre to just inside the edge.
 *
 * The four fractions match `ui/pygame_ui.py`'s ARROW_* constants. Widened and
 * thinned on 2026-09-20: the old 0.22/0.66/0.82 with a 0.13 wing drew six
 * short fat arrows per tile, and a hand of those reads as six little diagrams
 * rather than as six symbols. Same information, less visual weight. */
function drawArrow(parent, cx, cy, direction, className, headClass) {
  const a = directionAngle(direction);
  const [dx, dy] = [Math.cos(a), Math.sin(a)];
  const from = 0.20;
  const to = 0.72;
  el("line", {
    x1: cx + dx * from,
    y1: cy + dy * from,
    x2: cx + dx * to,
    y2: cy + dy * to,
    "stroke-width": 0.042,
    class: `arrow ${className}`,
  }, parent);
  const tip = 0.88;
  const wing = 0.105;
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
    // Visibility is CSS's: the mark shows under the pointer, not on all 24.
  }
}

function clearMarks() {
  for (const [id] of state.centres) {
    const group = ui.board.querySelector(`g[data-cell="${id}"]`);
    group.classList.remove("playable", "selected");
    group.querySelector('[data-role="hit"]').classList.remove("playable");
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

/* Draw the board before Python exists.
 *
 * EXP-019 measured boot at ~3.9 s and found it **compute-bound** — only ~10% of
 * a cold load is download — so there is no shortening it from here. What this
 * buys is a visible board during that wait instead of a blank panel. It is the
 * standard remedy for a wait, not a speed-up, and it does not make the page
 * playable one millisecond sooner.
 *
 * The cells come from `web/geometry.json`, generated by `scripts/build_web.py`
 * from `ui.session.layout` — the same function Python will return when it
 * starts. A test asserts the two agree, because a board drawn from a second
 * geometry would be exactly the divergence adr-013 forbids.
 */
async function drawInertBoard() {
  try {
    const shapes = await (await fetch("geometry.json")).json();
    const chosen = shapes[ui.variant.value] ?? shapes["5x5"];
    drawBoard(chosen);
    ui.boardWrap.classList.add("inert");
    mark("board");
  } catch (error) {
    // Not fatal: the live board replaces this one anyway. A page that refuses
    // to boot because a decoration failed would be worse than a blank wait.
    console.warn("early board unavailable", error);
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

/* Whether this device can hover.
 *
 * The rotation preview — the affordance this interface exists for — was wired
 * to `mouseenter`, which a touch screen never fires. On a phone that meant
 * tapping a rotation played it with no preview at all: the one thing a player
 * most needs to see before committing, invisible on the device most likely to
 * be handed to someone else. Read live rather than once, because a laptop with
 * a touchscreen can be either and a window can move between displays. */
function canHover() {
  try {
    return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  } catch {
    return true; // no matchMedia: assume a mouse and keep the old behaviour
  }
}

function renderRotations(options) {
  ui.rotations.textContent = "";
  state.armedRotation = null;
  const hovers = canHover();

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
    button.addEventListener("click", () => {
      /* With a mouse the preview has already happened on hover, so a click
       * commits. Without one, the first tap previews and arms, and only a
       * second tap on the same rotation plays it. */
      if (hovers || state.armedRotation === option.rotation) {
        playMove(option.rotation);
        return;
      }
      state.armedRotation = option.rotation;
      previewRotation(option);
      for (const other of ui.rotations.querySelectorAll("button.rot")) {
        other.classList.toggle("armed", other === button);
      }
      ui.hint.textContent = "Tap it again to place, or pick another rotation.";
    });
    ui.rotations.appendChild(button);
  }

  ui.rotationPanel.hidden = options.length === 0;
  if (options.length && !hovers) {
    ui.hint.textContent = "Tap a rotation to preview it, then tap again to place.";
  }
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

/* Whether the side to move is the one nobody automated.
 *
 * Read from the selector rather than assumed to be purple. The page hardcoded
 * the human as purple until 2026-09-21, which meant a visitor could only ever
 * experience the side of the board H1 says is favoured — on the page whose
 * whole point is the question of whether it is. */
function isHumanTurn() {
  if (ui.opponent.value === "human") return true;
  return state.snapshot.to_move === ui.side.value;
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
  if (!state.game || state.busy || state.selectedTile === null) return;
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
  if (!state.game || state.snapshot.terminal || isHumanTurn()) return;
  const kind = ui.opponent.value;
  const blocks = BLOCKING_SEATS.has(kind);
  state.busy = true;
  ui.undo.disabled = true;

  if (blocks) {
    /* Said before the freeze, not after. The 3x3 is solved outright from the
     * opening — 711,963 configurations — and adr-013 measured that at 7.5 s
     * under Node. A tab that stops responding for seven seconds with no
     * explanation is indistinguishable from one that has crashed. */
    say(
      "<b>The solver is searching.</b> It runs on the page&rsquo;s only thread, " +
        "so the tab will not respond until it answers.",
    );
    ui.hint.textContent = "Searching — the page is frozen until the solver replies.";
    document.body.classList.add("blocked");
  }
  // Yield so the human's move — and the warning above — paint before the
  // search takes the thread.
  await nextPaint();

  const started = performance.now();
  try {
    const result = state.game
      .agent_move_by_name(kind)
      .toJs({ dict_converter: Object.fromEntries });
    const elapsed = performance.now() - started;
    refresh(result.snapshot);
    paintArrows(placedTiles());
    animateFlips(result.flipped);
    /* The cost is reported rather than hidden. It is the one number a visitor
     * can check against adr-013's table, on their own machine and their own
     * browser — which is exactly what that ADR says it still owes. */
    say(
      blocks
        ? `${describe(result)} <span class="took">${(elapsed / 1000).toFixed(1)} s</span>`
        : describe(result),
    );
  } catch (error) {
    /* A seat can fail to build — the learner needs weights a clone does not
     * have. Saying so beats a dead board and a console nobody opened. */
    say(`<span class="bad">${String(error.message ?? error).split("\n")[0]}</span>`);
    console.error(error);
  } finally {
    document.body.classList.remove("blocked");
    state.busy = false;
    ui.undo.disabled = !state.snapshot.can_undo;
  }
}

/* Changing who you are playing does not throw the game away.
 *
 * `GameSession` names a seat per move and holds no agent, precisely so this is
 * possible — but the page restarted on every selector change anyway, which is
 * the complaint that started this: to try a different opponent you abandoned
 * the position. Only the board restarts now, because a different board is a
 * different game. The opponent and the colour you hold are just who is
 * answering from here, so the position stands and whoever now owns the move
 * takes it. Handing a live position from the heuristic to the solver is the
 * most interesting thing this page can do. */
async function onSeatChange() {
  if (!state.py || !state.game || state.busy) return;
  resetSelection();
  refresh(state.game.snapshot().toJs({ dict_converter: Object.fromEntries }));
  const seat = SEAT_LABELS[ui.opponent.value] ?? ui.opponent.value;
  const held = ui.side.value === "PURPLE" ? "purple" : "green";
  say(
    ui.opponent.value === "human"
      ? "Hotseat — both colours are yours."
      : `You hold <b>${held}</b>, against <b>${seat}</b>. The position stands.`,
  );
  await maybeAgentMove();
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
  ui.boardWrap.classList.remove("inert");
  ui.boot.hidden = true;
  ui.scoreline.hidden = false;
  refresh(state.snapshot);
  paintArrows([]);
  clearOverlay();
  clearMarks();
  ui.rotationPanel.hidden = true;
  say("");

  // When the visitor holds the second seat, the agent owns the opening and has
  // to take it, or the board waits for a move they cannot make.
  await maybeAgentMove();
}

/* -- boot ------------------------------------------------------------------ */

async function boot() {
  try {
    mark("chrome");
    await drawInertBoard();
    ui.bootText.textContent = "Downloading the Python runtime…";
    const { loadPyodide } = await import(`${PYODIDE}pyodide.mjs`);
    const py = await loadPyodide({ indexURL: PYODIDE });
    mark("runtime");

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
    // `ui/session.py`, where the test suite can reach it — a rule the page
    // broke once already by carrying its own subclass in this string.
    ui.bootText.textContent = "Starting the rules…";
    await py.runPythonAsync(`
import sys
sys.path.insert(0, ${JSON.stringify(PY_ROOT)})
from ui.session import GameSession
new_game = GameSession
`);

    state.py = py;
    mark("engine");
    ui.badge.textContent = "ready";
    ui.badge.classList.add("ready");
    ui.newGame.disabled = false;
    await startGame();
    mark("playable");
    reportMarks();
  } catch (error) {
    ui.badge.textContent = "failed";
    ui.badge.classList.add("failed");
    ui.bootText.textContent = "The engine did not start.";
    const note = ui.boot.querySelector(".boot-note");
    note.textContent = String(error).slice(0, 300);
    console.error(error);
  }
}

/* EXP-019's console surface. `fliphexMarks` is filled at boot; the solver probe
 * is a function so that nothing expensive runs unless it is asked for. */
window.fliphexBench = timeSolverOpening;
window.fliphexReport = fliphexReport;
window.fliphexReset = fliphexReset;

fillSeats(globalThis.location?.hostname);

ui.newGame.addEventListener("click", startGame);
// A different board is a different game, so this one restarts. The other two
// take effect on the position in front of you — see `onSeatChange`.
ui.variant.addEventListener("change", () => { if (state.py) startGame(); });
ui.opponent.addEventListener("change", onSeatChange);
ui.side.addEventListener("change", onSeatChange);
ui.undo.addEventListener("click", onUndo);
ui.cancel.addEventListener("click", resetSelection);

boot();

/* Exported for `web/test/page.test.mjs`, which drives the page through the DOM.
 * Harmless in a browser: this is already a module, and nothing imports it. */
export {
  boot,
  fillSeats,
  fliphexReport,
  fliphexReset,
  isLocalHost,
  onCellClick,
  onSeatChange,
  onTileClick,
  onUndo,
  playMove,
  readRuns,
  seatsFor,
  startGame,
  state,
  ui,
};
