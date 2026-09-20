/* Boot the real page headlessly and drive it through the DOM.
 *
 *     cd web && npm install && npm test
 *
 * Why this exists
 * ---------------
 * The Python half of this interface has over a thousand tests. The JavaScript
 * half had none, and two defects came out of that gap in a single sitting: a
 * `GameSession` subclass living inside a Python string in `app.js`, where no
 * test could reach it, and a null dereference in `startGame` that stopped the
 * page booting at all. Both were in code the suite structurally could not see.
 *
 * What it is
 * ----------
 * jsdom is the DOM standards implemented in JavaScript. It builds the document
 * tree a browser would build and runs scripts against it. It is **not** a
 * browser: no rendering, no layout, no CSS. So this catches logic — a wrong
 * selector, an unwired handler, a state machine in the wrong order — and
 * catches nothing visual. Overlapping hexagons and broken phone layout are
 * still a human's job, and EXP-019 still needs a real browser.
 *
 * `web/app.js` is imported **unmodified**. The only seam is
 * `globalThis.FLIPHEX_PYODIDE_URL`, which the page reads before choosing the
 * CDN — set here to the local package so the suite needs no network. A test
 * that rewrites its subject is testing something else.
 */

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { JSDOM } from "jsdom";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "..");

// -- harness -------------------------------------------------------------------

let failures = 0;

function check(description, condition, detail = "") {
  if (condition) {
    console.log(`  ok    ${description}`);
  } else {
    failures += 1;
    console.log(`  FAIL  ${description}${detail ? `\n          ${detail}` : ""}`);
  }
}

function equal(description, actual, expected) {
  check(description, actual === expected, `expected ${expected}, got ${actual}`);
}

// -- the browser jsdom does not provide ----------------------------------------

const html = readFileSync(`${WEB}/index.html`, "utf8");
const payload = readFileSync(`${WEB}/payload.json`, "utf8");

const dom = new JSDOM(html, { url: "http://localhost/", pretendToBeVisual: true });
const { window } = dom;

/* The page makes exactly one request. If it ever makes another, this throws
 * rather than quietly returning undefined — a second fetch would be a change
 * worth noticing. */
window.fetch = async (url) => {
  if (String(url).endsWith("payload.json")) {
    return { json: async () => JSON.parse(payload) };
  }
  throw new Error(`the page fetched something unexpected: ${url}`);
};

for (const key of ["document", "HTMLElement", "SVGElement", "Node", "Event"]) {
  globalThis[key] = window[key];
}
globalThis.window = window;
globalThis.fetch = window.fetch;

// Point the page at the installed pyodide instead of the CDN.
const require = createRequire(import.meta.url);
const pyodideDir = dirname(require.resolve("pyodide"));
globalThis.FLIPHEX_PYODIDE_URL = `${pyodideDir}/`;

// -- boot ----------------------------------------------------------------------

console.log("\n  FLIPHEX — web/app.js under jsdom\n");

const page = await import(pathToFileURL(`${WEB}/app.js`).href);

const deadline = Date.now() + 120_000;
while (page.ui.badge.textContent === "booting" && Date.now() < deadline) {
  await new Promise((r) => setTimeout(r, 100));
}

if (!page.ui.badge.classList.contains("ready")) {
  console.log(`  FAIL  the engine did not boot — badge: ${page.ui.badge.textContent}`);
  console.log(`        ${page.ui.boot.querySelector(".boot-note").textContent.trim()}`);
  process.exit(1);
}
check(`the engine boots — badge reads "${page.ui.badge.textContent}"`, true);

// -- EXP-019's instrumentation -------------------------------------------------

const marks = window.fliphexMarks;
check("boot marks are exposed for EXP-019", Array.isArray(marks) && marks.length === 4);
check(
  "the four marks are in order and cumulative",
  Array.isArray(marks) &&
    marks.map((m) => m.mark).join(",") === "chrome,runtime,engine,playable" &&
    marks.every((m, i) => i === 0 || m.totalMs >= marks[i - 1].totalMs),
);
check("the solver probe is available but not run", typeof window.fliphexBench === "function");

// -- the board -----------------------------------------------------------------

const board = page.ui.board;
check("the board is visible once the engine is ready", !board.hidden);
equal("25 hexagons are drawn", board.querySelectorAll("g.cell-group").length, 25);

const names = [...board.querySelectorAll(".cell-name")].map((n) => n.textContent);
check("cells are labelled A1 through E5", names[0] === "A1" && names.at(-1) === "E5");
equal("every hexagon carries a name", new Set(names).size, 25);

equal("purple holds 13 pieces", page.ui.hand.querySelectorAll("button.piece").length, 13);
equal("the score starts at zero", page.ui.scorePurple.textContent, "0");
check("purple moves first", page.ui.turn.textContent.includes("Purple"));

// -- choosing a move -----------------------------------------------------------

const pieces = page.ui.hand.querySelectorAll("button.piece");
pieces[0].dispatchEvent(new window.Event("click"));
equal(
  "choosing a piece marks every legal cell",
  board.querySelectorAll("g.cell-group.playable").length,
  25,
);
/* Re-queried, not reused: `renderHand` rebuilds the buttons on every
 * selection, so the node clicked above is detached by now. Worth a comment
 * because the first version of this check asserted against the stale one and
 * reported a page defect that did not exist. */
const pressed = [...page.ui.hand.querySelectorAll("button.piece")].filter(
  (b) => b.getAttribute("aria-pressed") === "true",
);
equal("exactly one piece reads as pressed", pressed.length, 1);

const target = board.querySelectorAll("g.cell-group.playable")[12];
target.querySelector('[data-role="hit"]').dispatchEvent(new window.Event("click"));
const rotations = page.ui.rotations.querySelectorAll("button.rot");
check("choosing a cell offers its distinct rotations", rotations.length > 0);
check("the rotation panel opens", !page.ui.rotationPanel.hidden);
check(
  "each rotation shows a signed net swing",
  [...rotations].every((r) => /^[+-]?\d+$/.test(r.querySelector(".net").textContent)),
);

rotations[0].dispatchEvent(new window.Event("mouseenter"));
check(
  "hovering a rotation previews it on the board",
  board.querySelector("#overlay").childNodes.length > 0,
);

// -- playing -------------------------------------------------------------------

await page.playMove(0);
await new Promise((r) => setTimeout(r, 500));

equal("the move lands and the heuristic replies", page.state.snapshot.ply, 2);
equal(
  "exactly two cells are coloured",
  [...board.querySelectorAll('[data-role="fill"]')].filter(
    (n) => !n.getAttribute("class").includes("cell-empty"),
  ).length,
  2,
);
check(
  "placed tiles show the arrows they fired",
  board.querySelectorAll('[data-role="arrows"] line').length > 0,
);
check(
  `commentary describes the move — "${page.ui.commentary.textContent.trim()}"`,
  page.ui.commentary.textContent.includes("played"),
);
check("the selection is cleared after a move", page.state.selectedTile === null);
check("undo is offered", !page.ui.undo.disabled);

// -- undo ----------------------------------------------------------------------

page.onUndo();
equal("undo takes back both plies", page.state.snapshot.ply, 0);
equal(
  "the board is empty again",
  [...board.querySelectorAll('[data-role="fill"]')].filter(
    (n) => !n.getAttribute("class").includes("cell-empty"),
  ).length,
  0,
);

// -- the reduced boards --------------------------------------------------------

page.ui.variant.value = "3x3";
await page.startGame();
equal("switching to the 3x3 redraws nine cells", board.querySelectorAll("g.cell-group").length, 9);
equal(
  "the 3x3 is dealt its reduced hand, not the full deck",
  page.ui.hand.querySelectorAll("button.piece").length,
  5,
);

page.ui.variant.value = "5x3";
await page.startGame();
equal("the 5x3 redraws fifteen cells", board.querySelectorAll("g.cell-group").length, 15);
equal("the 5x3 is dealt eight pieces", page.ui.hand.querySelectorAll("button.piece").length, 8);

// -- the deployed seat list ----------------------------------------------------

const seats = [...page.ui.opponent.options].map((o) => o.value);
check(
  "the published page offers nothing above the heuristic (adr-013, 2026-09-21)",
  seats.every((s) => s === "human" || s === "heuristic"),
  `offers: ${seats.join(", ")}`,
);

// -- done ----------------------------------------------------------------------

console.log(
  failures
    ? `\n  ${failures} check(s) failed\n`
    : "\n  all checks passed — jsdom is not a browser; EXP-019 still needs one\n",
);
process.exit(failures ? 1 : 0);
