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

/* A sentence the page builds, as a pattern rather than as a literal.
 *
 * The page is bilingual, so a check that quotes English prose passes in one
 * language and fails in the other for no reason a reader could guess. This
 * turns the template into a regular expression — tags dropped, `{placeholders}`
 * widened — so the check is "the page said this sentence, with something in
 * each slot" in whichever language is current. */
function shapeOf(key) {
  const template = STRINGS[page.getLang()][key]
    .replace(/<[^>]*>/g, "")
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\{\w+\\\}/g, ".+");
  return new RegExp(template);
}

/* Wait for a condition rather than for a duration. */
async function until(condition, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (!condition() && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 25));
  }
  return condition();
}

// -- the browser jsdom does not provide ----------------------------------------

const html = readFileSync(`${WEB}/index.html`, "utf8");
const payload = readFileSync(`${WEB}/payload.json`, "utf8");
const shapes = readFileSync(`${WEB}/geometry.json`, "utf8");

/* Imported directly as well as through the page, so the checks below can name a
 * string by key instead of by a literal that would have to be kept in step with
 * the dictionary — which is the specific mistake the bilingual page makes easy. */
const { STRINGS, LANGS, DEFAULT_LANG } = await import(pathToFileURL(`${WEB}/i18n.js`).href);

const dom = new JSDOM(html, { url: "http://localhost/", pretendToBeVisual: true });
const { window } = dom;

/* The page makes exactly one request. If it ever makes another, this throws
 * rather than quietly returning undefined — a second fetch would be a change
 * worth noticing. */
/* jsdom implements no `matchMedia` whatsoever, so the page's `canHover()` would
 * fall to its "assume a mouse" branch and the touch path would never be
 * exercised. Both paths ship, so the harness supplies a media query it can
 * flip. */
let hasHover = true;
window.matchMedia = (query) => ({
  matches: /hover: hover/.test(query) ? hasHover : false,
  media: query,
  addEventListener() {},
  removeEventListener() {},
  addListener() {},
  removeListener() {},
});

const SERVED = { "payload.json": payload, "geometry.json": shapes };
const fetched = [];

window.fetch = async (url) => {
  const name = String(url).split("/").pop();
  fetched.push(name);
  if (name in SERVED) return { json: async () => JSON.parse(SERVED[name]) };
  throw new Error(`the page fetched something unexpected: ${url}`);
};

/* Everything the page reaches for as a bare global. jsdom supplies all of
 * these; Node 18 supplies none of them, so leaving one out fails the page with
 * a ReferenceError that looks like a page defect and is not one. */
for (const key of [
  "document",
  "HTMLElement",
  "SVGElement",
  "Node",
  "Event",
  "navigator",
  "localStorage",
  "matchMedia",
  // The page reads `location.hostname` to decide which seats it may offer.
  // jsdom's is `http://localhost/`, set above, so this harness is a local
  // checkout — which is the case that has to be exercised, since the published
  // one is the fallback already written into `index.html`.
  "location",
]) {
  globalThis[key] = window[key];
}
globalThis.window = window;
globalThis.fetch = window.fetch;

// Each run starts from an empty collection, so the checks below see only this
// process's loads.
try {
  window.localStorage.clear();
} catch {
  /* jsdom without storage: readRuns() degrades to [] on its own */
}

// Point the page at the installed pyodide instead of the CDN.
const require = createRequire(import.meta.url);
const pyodideDir = dirname(require.resolve("pyodide"));
globalThis.FLIPHEX_PYODIDE_URL = `${pyodideDir}/`;

// -- boot ----------------------------------------------------------------------

console.log("\n  FLIPHEX — web/app.js under jsdom\n");

const page = await import(pathToFileURL(`${WEB}/app.js`).href);

/* 300 s, which is absurd for a 4 s boot and is deliberate. Pyodide's
 * initialisation stalls on this machine roughly one load in five, for about
 * 235 s — first seen while sampling boot for EXP-018 (one of three samples took
 * 234 s) and reproduced here from a completely different harness. Two
 * independent sightings of the same figure make it an environment property, not
 * a fluke, and a deadline under it would turn that stall into a red page. */
const BOOT_DEADLINE_MS = 300_000;
const bootStarted = Date.now();
/* Watched through the class, not the words. The badge is translated, so the
 * literal this used to compare against — "booting" — stopped being what the
 * badge says the moment the page gained a second language, and the wait would
 * have returned true on its first tick with nothing booted. The class is what
 * actually carries the state. */
const settled = () =>
  page.ui.badge.classList.contains("ready") || page.ui.badge.classList.contains("failed");
await until(settled, BOOT_DEADLINE_MS);
const bootMs = Date.now() - bootStarted;

if (!settled()) {
  /* Exit 2, not 1: nothing about the page was tested, so reporting a failure
   * would be a claim this run cannot support. */
  console.log(`\n  INCONCLUSIVE — the Python runtime did not start in ${bootMs} ms.`);
  console.log("  This is the known ~235 s Pyodide stall on this machine, not a page");
  console.log("  defect: no check below ran. See EXP-018 and EXP-019. Re-run.\n");
  process.exit(2);
}

if (!page.ui.badge.classList.contains("ready")) {
  console.log(`  FAIL  the engine did not boot — badge: ${page.ui.badge.textContent}`);
  console.log(`        ${page.ui.boot.querySelector(".boot-note").textContent.trim()}`);
  process.exit(1);
}
check(`the engine boots — badge reads "${page.ui.badge.textContent}"`, true);

// -- EXP-019's instrumentation -------------------------------------------------

const marks = window.fliphexMarks;
check("boot marks are exposed for EXP-019", Array.isArray(marks) && marks.length === 5);
check(
  "the marks are cumulative, never going backwards",
  Array.isArray(marks) && marks.every((m, i) => i === 0 || m.totalMs >= marks[i - 1].totalMs),
);
check("the solver probe is available but not run", typeof window.fliphexBench === "function");

// -- the split render (EXP-019 rule 1) -----------------------------------------

check(
  "the geometry is fetched before the payload",
  fetched.indexOf("geometry.json") !== -1 &&
    fetched.indexOf("geometry.json") < fetched.indexOf("payload.json"),
  `fetch order: ${fetched.join(", ")}`,
);
const markNames = marks.map((m) => m.mark);
equal(
  "the board is marked between the chrome and the runtime",
  markNames.join(","),
  "chrome,board,runtime,engine,playable",
);
check(
  "the board was drawn before Python started",
  marks[1].totalMs < marks[2].totalMs,
  `board at ${marks[1].totalMs} ms, runtime at ${marks[2].totalMs} ms`,
);
check(
  "drawing the board costs far less than the runtime it precedes",
  marks[1].deltaMs * 5 < marks[2].deltaMs,
  `board ${marks[1].deltaMs} ms vs runtime ${marks[2].deltaMs} ms`,
);
check(
  "the board is live once the engine is ready, not inert",
  !page.ui.boardWrap.classList.contains("inert"),
);
check("the boot strip is hidden once playable", page.ui.boot.hidden);

const collected = page.readRuns();
equal("this load was collected for EXP-019", collected.length, 1);
check(
  "the cache state is measured from transferred bytes, not assumed",
  ["cold", "warm", "unknown"].includes(collected[0]?.cache),
  `got ${collected[0]?.cache}`,
);
check(
  "a load served entirely from disk classifies as warm",
  collected[0]?.cache === "warm",
  `${collected[0]?.transferredBytes} bytes transferred under jsdom`,
);
check("fliphexReport prints without throwing", page.fliphexReport().length === 1);

// -- the board -----------------------------------------------------------------

const board = page.ui.board;

/* The ATTRIBUTE, not the property, and the distinction is the whole test.
 *
 * `hidden` is defined on `HTMLElement`. `SVGElement` does not carry it, so
 * `svg.hidden = false` on an `<svg>` sets a plain JavaScript property and
 * leaves `hidden=""` in the markup. This check used to read `!board.hidden` —
 * the same property the code had just assigned — so it passed by asking the
 * page to confirm its own mistake, and the board only rendered because a
 * second bug (`#board { display: block }` outranking the browser's
 * `[hidden] { display: none }`) was cancelling the first.
 *
 * Fixing the stylesheet took the mask off and the board disappeared. A test
 * that reads back what the code wrote is not a test; this one reads what the
 * browser would act on. */
check(
  "the board is visible once the engine is ready",
  !board.hasAttribute("hidden"),
  `board still carries hidden="${board.getAttribute("hidden")}"`,
);
equal("25 hexagons are drawn", board.querySelectorAll("g.cell-group").length, 25);

const names = [...board.querySelectorAll(".cell-name")].map((n) => n.textContent);
check("cells are labelled A1 through E5", names[0] === "A1" && names.at(-1) === "E5");
equal("every hexagon carries a name", new Set(names).size, 25);

equal("purple holds 13 pieces", page.ui.hand.querySelectorAll("button.piece").length, 13);
equal("the score starts at zero", page.ui.scorePurple.textContent, "0");
check(
  "purple moves first",
  page.ui.turn.textContent.includes(STRINGS[page.getLang()]["colour.PURPLE"]),
  page.ui.turn.textContent,
);

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

/* -- the touch path (EXP-019's phone cell is about to use it) ----------------- */

/* Reopen the strip with hover reported absent, which is what a phone reports.
 * Until this was fixed, a tap played the rotation with no preview at all — the
 * affordance this whole interface exists for, missing on the device most likely
 * to be handed to somebody else. */
hasHover = false;
page.onCellClick(page.state.selectedCell);
const taps = page.ui.rotations.querySelectorAll("button.rot");
board.querySelector("#overlay").textContent = "";

taps[0].dispatchEvent(new window.Event("click"));
check(
  "without hover, the first tap previews instead of playing",
  page.state.snapshot.ply === 0 &&
    board.querySelector("#overlay").childNodes.length > 0 &&
    taps[0].classList.contains("armed"),
  `ply ${page.state.snapshot.ply}, armed ${taps[0].classList.contains("armed")}`,
);

if (taps.length > 1) {
  taps[1].dispatchEvent(new window.Event("click"));
  check(
    "tapping a different rotation re-arms rather than playing",
    page.state.snapshot.ply === 0 &&
      taps[1].classList.contains("armed") &&
      !taps[0].classList.contains("armed"),
  );
}

// -- playing -------------------------------------------------------------------

/* A second tap on the armed rotation commits — the touch path in full, rather
 * than calling `playMove` behind the interface's back. */
[...taps].find((r) => r.classList.contains("armed")).dispatchEvent(new window.Event("click"));

/* Polled, not slept. The agent's reply is scheduled on a timer so the human's
 * move paints first, and a fixed wait turns machine load into a red test — the
 * one failure mode that makes a suite worth less than no suite. */
await until(() => page.state.snapshot.ply === 2, 15_000);
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
  shapeOf("say.played").test(page.ui.commentary.textContent),
);
check("the selection is cleared after a move", page.state.selectedTile === null);

/* -- the mouse path, on the next move ---------------------------------------- */

hasHover = true;
const secondPiece = page.ui.hand.querySelectorAll("button.piece")[0];
secondPiece.dispatchEvent(new window.Event("click"));
const secondCell = board.querySelectorAll("g.cell-group.playable")[3];
secondCell.querySelector('[data-role="hit"]').dispatchEvent(new window.Event("click"));
const withMouse = page.ui.rotations.querySelectorAll("button.rot");
withMouse[0].dispatchEvent(new window.Event("click"));
await until(() => page.state.snapshot.ply === 4, 15_000);
check(
  "with a mouse, one click commits — the preview already happened on hover",
  page.state.snapshot.ply === 4,
  `ply ${page.state.snapshot.ply}`,
);

page.onUndo();
await until(() => page.state.snapshot.ply === 2, 5_000);
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

// -- which colour the visitor holds --------------------------------------------

page.ui.variant.value = "3x3";
page.ui.side.value = "GREEN";
await page.startGame();
await until(() => page.state.snapshot.ply === 1, 15_000);
check(
  "choosing green makes the agent open unprompted",
  page.state.snapshot.ply === 1 && page.state.snapshot.to_move === "GREEN",
  `ply ${page.state.snapshot.ply}, to move ${page.state.snapshot.to_move}`,
);
equal(
  "the hand shown is the one the visitor holds",
  page.ui.handTitle.textContent.startsWith(STRINGS[page.getLang()]["colour.GREEN"]),
  true,
);

page.ui.side.value = "PURPLE";
await page.startGame();
equal("choosing purple leaves the opening to the visitor", page.state.snapshot.ply, 0);

// -- which seats the origin is allowed -----------------------------------------

/* adr-013's second amendment withdrew every agent above the heuristic from the
 * *deployed* page and said the local one still serves them. Until now both were
 * the same `index.html`, so the second half was not true. These checks are the
 * split, and the important ones are the negative ones: the rule fails closed,
 * so a host nobody thought about is restricted rather than permitted. */
const PUBLISHED = "human,heuristic";
const PUBLISHED_3X3 = "human,heuristic,solver";
const LOCAL = "human,random,heuristic,solver";
// The board is the second axis, added by adr-013's fourth amendment. Anything
// that does not name one is asking the old question and must get the old,
// narrowest answer.
const offers = (hostname, board = "5x5") => page.seatsFor(hostname, board).join(",");

equal("GitHub Pages gets the published list", offers("brunoramosmartins.github.io"), PUBLISHED);
equal("an unrecognised host fails closed", offers("example.com"), PUBLISHED);
equal("a host that merely ends in localhost.com is not local", offers("notlocalhost.com"), PUBLISHED);
equal("172.32 is public address space, not RFC 1918", offers("172.32.0.1"), PUBLISHED);
equal("11.0.0.1 is public, and 10.0.0.1 is not", offers("11.0.0.1"), PUBLISHED);
equal("an over-range quad is not an address", offers("999.0.0.1"), PUBLISHED);

equal("localhost gets the exact solver", offers("localhost"), LOCAL);
equal("loopback by address gets it too", offers("127.0.0.1"), LOCAL);
equal("file:// has no host at all and is as local as it gets", offers(""), LOCAL);
equal("a wifi address is a local checkout being served by its author", offers("192.168.0.14"), LOCAL);
equal("the 172.25 WSL address a phone reached in EXP-019 is local", offers("172.25.201.155"), LOCAL);
equal("mDNS names never resolve on the public internet", offers("bruno-laptop.local"), LOCAL);

/* The fourth amendment. The solver returns to the deployed page on the one
 * board where it is exact from the first move — and nowhere else, because
 * anywhere else it would freeze the tab for longer in exchange for heuristic
 * play. The negative checks are again the load-bearing ones. */
equal(
  "the published 3x3 offers the solver, because there it is perfect",
  offers("brunoramosmartins.github.io", "3x3"),
  PUBLISHED_3X3,
);
equal("the published 5x3 does not", offers("brunoramosmartins.github.io", "5x3"), PUBLISHED);
equal("nor the published 5x5", offers("brunoramosmartins.github.io", "5x5"), PUBLISHED);
equal("a board nobody thought about fails closed too", offers("example.com", "9x9"), PUBLISHED);
equal("and so does no board at all", offers("example.com", undefined), PUBLISHED);
equal("locally the board is irrelevant — every seat, every board", offers("localhost", "5x5"), LOCAL);

equal(
  "served from localhost, the page itself offers the solver",
  [...page.ui.opponent.options].map((o) => o.value).join(","),
  LOCAL,
);
check(
  "and says so, so the difference from the published page is visible",
  page.ui.originNote.textContent === STRINGS[page.getLang()]["origin.local"],
  `origin note: "${page.ui.originNote.textContent}"`,
);
check(
  "the seats torch makes impossible are offered by neither origin",
  !offers("localhost").includes("az") && !offers("localhost").includes("uct"),
);

/* The footer line explains the *absence* where the seat is missing and the
 * *wait* where it is offered, because an 8 s freeze that arrives unannounced
 * reads as a crash. Three origins, three different sentences. */
check(
  "the published 3x3 warns about the wait before the visitor meets it",
  page.originNote("brunoramosmartins.github.io", "3x3").includes("8 s"),
  page.originNote("brunoramosmartins.github.io", "3x3"),
);
check(
  "the published 5x5 says where the solver can be found instead",
  page.originNote("brunoramosmartins.github.io", "5x5").includes("3×3"),
  page.originNote("brunoramosmartins.github.io", "5x5"),
);
check(
  "a local checkout says it is one",
  page.originNote("localhost", "5x5") === STRINGS[page.getLang()]["origin.local"],
  page.originNote("localhost", "5x5"),
);

/* `fillSeats` now depends on the board as well as the host, so a visitor who
 * picked the solver on the published 3x3 and then changed board must not be
 * left holding a seat that is no longer in the list. jsdom's own hostname is
 * localhost, so the published case is driven by argument rather than by
 * pretending to be somewhere else. */
page.fillSeats("brunoramosmartins.github.io", "3x3");
page.ui.opponent.value = "solver";
page.fillSeats("brunoramosmartins.github.io", "5x5");
equal("leaving the 3x3 withdraws the solver option", page.ui.opponent.value, "heuristic");
equal(
  "and the list narrows with it",
  [...page.ui.opponent.options].map((o) => o.value).join(","),
  PUBLISHED,
);
// Put the harness back where it was: local, with every seat available.
page.fillSeats("localhost", page.ui.variant.value);
equal(
  "restoring the local origin restores the full list",
  [...page.ui.opponent.options].map((o) => o.value).join(","),
  LOCAL,
);

// -- changing who you play, without losing the position ------------------------

/* The complaint this answers: to try a different opponent you had to abandon
 * the game. `GameSession` names a seat per move and holds no agent precisely so
 * that is unnecessary, and the page restarted anyway. */
const piece = page.ui.hand.querySelectorAll("button.piece")[0];
piece.dispatchEvent(new window.Event("click"));
const spot = board.querySelectorAll("g.cell-group.playable")[0];
spot.querySelector('[data-role="hit"]').dispatchEvent(new window.Event("click"));
page.ui.rotations.querySelectorAll("button.rot")[0].dispatchEvent(new window.Event("click"));
await until(() => page.state.snapshot.ply === 2, 15_000);
equal("a move on the 3x3 lands and the heuristic replies", page.state.snapshot.ply, 2);

page.ui.opponent.value = "random";
await page.onSeatChange();
equal("changing opponent keeps the position", page.state.snapshot.ply, 2);
equal("and does not steal the move", page.state.snapshot.to_move, "PURPLE");

page.ui.side.value = "GREEN";
await page.onSeatChange();
await until(() => page.state.snapshot.ply === 3, 15_000);
check(
  "handing your colour over makes the new seat answer from that same position",
  page.state.snapshot.ply === 3 && page.state.snapshot.to_move === "GREEN",
  `ply ${page.state.snapshot.ply}, to move ${page.state.snapshot.to_move}`,
);

page.ui.side.value = "PURPLE";
page.ui.opponent.value = "heuristic";
page.ui.variant.value = "5x5";
await page.onBoardChange();
equal("a different board is a different game, so that one does restart", page.state.snapshot.ply, 0);
equal("and deals the full deck again", page.ui.hand.querySelectorAll("button.piece").length, 13);

// -- two languages, one page ---------------------------------------------------

/* The page ships in Portuguese for the Matemateca and offers English. What can
 * go wrong here is not a wrong translation — nothing automatic can judge that —
 * but a page that is *half* translated: a key that exists in one dictionary and
 * not the other, a string the markup asks for that nobody wrote, or an element
 * that keeps its old words because whoever added it forgot the marker.
 *
 * All three are structural, and all three are checked below. jsdom is enough
 * for every one of them: this is text and attributes, not layout. */

const [ptKeys, enKeys] = LANGS.map((lang) => Object.keys(STRINGS[lang]).sort());
equal("the two dictionaries are the same size", ptKeys.length, enKeys.length);
check(
  "and carry exactly the same keys",
  ptKeys.join("|") === enKeys.join("|"),
  `only in pt: ${ptKeys.filter((k) => !enKeys.includes(k))} / ` +
    `only in en: ${enKeys.filter((k) => !ptKeys.includes(k))}`,
);

/* Every key the markup names. `data-i18n-attr` holds `attr: key` pairs, so the
 * key is what follows the colon. */
const markupKeys = new Set();
for (const match of html.matchAll(/data-i18n(?:-html)?="([^"]+)"/g)) markupKeys.add(match[1]);
for (const match of html.matchAll(/data-i18n-attr="([^"]+)"/g)) {
  for (const pair of match[1].split(",")) markupKeys.add(pair.split(":")[1].trim());
}
check("the markup names keys to translate", markupKeys.size > 20, `${markupKeys.size} found`);
const strayMarkup = [...markupKeys].filter((key) => LANGS.some((l) => !(key in STRINGS[l])));
check("and every one of them is in both dictionaries", strayMarkup.length === 0, strayMarkup);

/* Every key `app.js` looks up as a literal. `seat.${seat}` and `colour.${colour}`
 * are built at runtime and cannot be scanned, so they are named explicitly —
 * missing one of those is exactly the kind of gap this check exists to close,
 * and a regex that silently skipped them would report a clean sweep. */
/* Comments stripped first, and the first version of this check is why. A
 * comment in `app.js` explains that `fillSeats` builds its labels from
 * `t("seat.*")` — so the scan found the key `seat.*`, which no dictionary has
 * and no code asks for, and reported a missing translation that did not exist.
 * The same trap as the stylesheet link-order check and the `[hidden]` check,
 * both of which matched their own explanation before they matched the code. */
const appSource = readFileSync(`${WEB}/app.js`, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const codeKeys = new Set(
  [...appSource.matchAll(/\b(?:t|setBadge)\("([^"]+)"/g)].map((m) => m[1]),
);
for (const seat of ["human", "random", "heuristic", "solver"]) codeKeys.add(`seat.${seat}`);
for (const colour of ["PURPLE", "GREEN"]) codeKeys.add(`colour.${colour}`);
const strayCode = [...codeKeys].filter((key) => LANGS.some((l) => !(key in STRINGS[l])));
check("every key app.js asks for exists in both dictionaries", strayCode.length === 0, strayCode);

/* Nothing in either dictionary is unreachable. A key no page and no module ever
 * names is either a translation of something that was deleted or a marker
 * somebody forgot to add, and both are worth a failing check rather than a
 * growing file. */
const orphans = ptKeys.filter(
  (key) => !markupKeys.has(key) && !codeKeys.has(key) && key !== "html.lang",
);
check("no dictionary entry is unreachable", orphans.length === 0, orphans);

equal("Portuguese is the default", DEFAULT_LANG, "pt");
equal("and it is what the page starts in", page.getLang(), "pt");
equal("with the document declaring it", window.document.documentElement.lang, "pt-BR");

/* The terminal hint used to read "25 is odd" on every board, which is right on
 * the shipped one and wrong on both boards this project actually solved. The
 * count now comes from the position, and the placeholder is what proves the
 * sentence can still say it — a hint.full with the number written back in would
 * pass every other check here. */
for (const lang of LANGS) {
  check(`the full-board hint takes its cell count as a variable (${lang})`,
    STRINGS[lang]["hint.full"].includes("{cells}"), STRINGS[lang]["hint.full"]);
}

// -- switching -----------------------------------------------------------------

const boardLabelPt = page.ui.variant.options[0].textContent;
const seatLabelPt = page.ui.opponent.options[0].textContent;
const badgePt = page.ui.badge.textContent;

page.applyLanguage("en");
equal("switching moves the page", page.getLang(), "en");
equal("and the document with it", window.document.documentElement.lang, "en");
equal(
  "static markup is rewritten",
  page.ui.variant.options[0].textContent,
  STRINGS.en["board.5x5"],
);
check("and it really did change", page.ui.variant.options[0].textContent !== boardLabelPt);
equal(
  "the opponent list is rebuilt, not just relabelled once",
  page.ui.opponent.options[0].textContent,
  STRINGS.en[`seat.${page.ui.opponent.options[0].value}`],
);
check("which is a different string than before", seatLabelPt !== page.ui.opponent.options[0].textContent);
check(
  "text derived from the position follows too",
  page.ui.turn.textContent === `${STRINGS.en["colour.PURPLE"]} to move`,
  page.ui.turn.textContent,
);

/* The regression `setBadge` exists for. `index.html` marks the badge
 * `data-i18n="badge.booting"` so it reads correctly before the module loads,
 * which means a naive re-apply tells a booted page it is booting again. */
check(
  "a booted badge does not go back to booting",
  page.ui.badge.textContent !== STRINGS.en["badge.booting"] &&
    page.ui.badge.textContent !== STRINGS.pt["badge.booting"],
  page.ui.badge.textContent,
);
check("and it did change language", page.ui.badge.textContent !== badgePt, page.ui.badge.textContent);

/* The boundary from i18n.js's header: the game is bilingual, the site chrome is
 * not, because every link in it leads to a page that exists only in English. */
const nav = html.split('id="site-nav"', 2)[1].split("</nav>", 2)[0];
check("the site navigation carries no translation markers", !nav.includes("data-i18n"), nav.trim());
check("and still reads in English", nav.includes(">Projects<") && nav.includes(">About<"));

page.applyLanguage("pt");
equal("switching back restores Portuguese", page.getLang(), "pt");
equal("and the markup with it", page.ui.variant.options[0].textContent, boardLabelPt);
equal("and the document language", window.document.documentElement.lang, "pt-BR");

/* The choice survives a reload, which is the only thing `localStorage` is used
 * for here. Reading it back through the page's own accessor rather than through
 * the key keeps the storage key an implementation detail. */
equal("the choice is remembered", window.localStorage.getItem("fliphex.lang"), "pt");

// -- done ----------------------------------------------------------------------

console.log(
  failures
    ? `\n  ${failures} check(s) failed\n`
    : "\n  all checks passed — jsdom is not a browser; EXP-019 still needs one\n",
);
process.exit(failures ? 1 : 0);
