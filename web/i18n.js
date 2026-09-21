/* Two languages for one page.
 *
 * WHY THIS EXISTS
 * ---------------
 * The physical game is going on display at the Matemateca, IME-USP's
 * mathematics exhibition space, where the visitors are Brazilian. The rest of
 * the portfolio is in English, and so was this page. Neither audience should
 * have to read the other one's language to play, so the page carries both and
 * **Portuguese is the default**: the exhibition is the reason the page exists,
 * and a visitor arriving from the English site can switch in one click.
 *
 * WHAT IS TRANSLATED, AND WHAT IS NOT
 * -----------------------------------
 * The *game* is translated: every label, hint, status line and sentence this
 * interface produces. The *site chrome* is not — the header navigation and the
 * footer links point at pages of brunoramosmartins.github.io that exist only in
 * English, and a translated label on a link to an English page is a promise the
 * destination does not keep. `site.css`'s header comment draws the same border
 * for a different reason, and it is the same border: the frame belongs to the
 * building, the canvas belongs to the game.
 *
 * Identifiers stay English, here and everywhere. The keys below, the code, the
 * comments and every file in this repository are English; only the *values* are
 * bilingual. This is UI copy for an audience, not documentation for a reader.
 *
 * THE STATIC SIDE SHIPS IN PORTUGUESE
 * -----------------------------------
 * `index.html` is written in Portuguese and declares `lang="pt-BR"`, rather
 * than shipping English and being rewritten on load. A module script is
 * deferred, so the alternative shows every Portuguese-speaking visitor a flash
 * of English before the swap — on the default path, which is the one that has
 * to be right. English costs a repaint instead, which is the correct place to
 * put the cost.
 *
 * WHAT A MISSING KEY DOES
 * -----------------------
 * It returns the key itself, visibly. A silent fallback to the other language
 * produces a page that is subtly half-translated and looks deliberate;
 * `hint.pick` sitting in the interface does not. `test/page.test.mjs` asserts
 * the two dictionaries have identical key sets, so this should be unreachable.
 */

export const LANGS = ["pt", "en"];

/* Portuguese, for the reason in the header comment. */
export const DEFAULT_LANG = "pt";

/* Per-viewer convenience, not state this page depends on. Every access is
 * guarded: storage throws in a private window and comes back empty after a
 * site-data clear, and a page that cannot remember a preference must still
 * render. */
const STORAGE_KEY = "fliphex.lang";

export const STRINGS = {
  pt: {
    /* -- document ---------------------------------------------------------- */
    "html.lang": "pt-BR",
    "meta.description":
      "Jogue FLIPHEX no navegador. As regras rodam no mesmo motor Python que produziu as soluções exatas do projeto.",
    "skip.link": "Pular para o conteúdo",
    "nav.toggle": "Abrir e fechar a navegação",

    /* -- controls ---------------------------------------------------------- */
    "label.board": "Tabuleiro",
    "board.5x5": "5×5 — o jogo publicado",
    "board.5x3": "5×3 — resolvido exatamente",
    "board.3x3": "3×3 — resolvido exatamente",
    "label.side": "Você joga",
    "side.purple": "roxo — joga primeiro",
    "side.green": "verde — joga depois",
    "label.opponent": "Contra",
    "button.newGame": "Novo jogo",
    "lang.group": "Idioma",
    "lang.pt": "Ler em português",
    "lang.en": "Read in English",

    /* -- seats ------------------------------------------------------------- */
    "seat.human": "um segundo jogador",
    "seat.random": "o agente aleatório",
    "seat.heuristic": "o agente heurístico",
    "seat.solver": "o solver exato",

    "origin.local": "Cópia local — todos os assentos são oferecidos, em todos os tabuleiros.",
    "origin.solverHere":
      "O solver joga este tabuleiro perfeitamente. Precisa de uns 8 s para a abertura.",
    "origin.solverElsewhere":
      "O solver exato é oferecido no 3×3, onde joga perfeitamente desde o primeiro lance.",

    /* -- board and boot ---------------------------------------------------- */
    "board.aria": "Tabuleiro do FLIPHEX",
    "boot.engine": "Iniciando o motor de regras…",
    "boot.note":
      "Este tabuleiro é de verdade; ele só não é jogável até o motor subir. A página roda o Python real do projeto, compilado para WebAssembly — as regras nunca são reimplementadas em JavaScript.",
    "boot.runtime": "Baixando o runtime do Python…",
    "boot.unpack": "Descompactando o motor…",
    "boot.rules": "Iniciando as regras…",
    "boot.failed": "O motor não subiu.",

    "badge.booting": "subindo",
    "badge.ready": "pronto",
    "badge.readyIn": "pronto em {seconds}s",
    "badge.failed": "falhou",

    /* -- colours ----------------------------------------------------------- */
    "colour.PURPLE": "Roxo",
    "colour.GREEN": "Verde",
    "colour.purple": "roxo",
    "colour.green": "verde",

    /* -- panels ------------------------------------------------------------ */
    "panel.hand": "Suas peças",
    "button.undo": "Desfazer",
    "panel.rotation": "Rotação",
    "button.cancel": "Cancelar",
    "hint.net":
      "Passe o cursor para pré-visualizar. <b>Saldo</b> é peças ganhas menos peças devolvidas.",
    "hand.title": "{colour} — restam {count}",
    "piece.title": "{archetype} — {arrows} seta(s), {rotations} rotação(ões) distinta(s)",

    /* -- status ------------------------------------------------------------ */
    "turn.toMove": "{colour} joga",
    "turn.wins": "{colour} venceu",

    "hint.pick": "Escolha uma peça, depois uma célula.",
    "hint.thinking": "O agente está pensando…",
    "hint.cell": "Agora escolha uma célula destacada.",
    "hint.rotation": "Escolha uma rotação.",
    "hint.tapAgain": "Toque de novo para colocar, ou escolha outra rotação.",
    "hint.tapPreview": "Toque numa rotação para pré-visualizar, depois toque de novo para colocar.",
    "hint.searching": "Buscando — a página fica travada até o solver responder.",
    "hint.full": "O tabuleiro está cheio. {cells} é ímpar, então empate não existe.",

    /* -- commentary -------------------------------------------------------- */
    "say.searching":
      "<b>O solver está buscando.</b> Ele roda na única thread da página, então a aba não responde até ele terminar.",
    "say.played": "<b>{who}</b> jogou <b>{archetype}</b> em <b>{cell}</b>",
    "say.flipping": "virando {count}",
    "say.handingBack": "devolvendo {count}",
    "say.nothing": "sem nada para virar",
    "say.hotseat": "Mesa compartilhada — as duas cores são suas.",
    "say.standing": "Você tem <b>{held}</b>, contra <b>{seat}</b>. A posição continua de pé.",
    "say.withdrawn": "Este tabuleiro não oferece {gone}, então você está jogando <b>{now}</b>.",

    /* -- rules summary ----------------------------------------------------- */
    "notes.summary": "Como funciona",
    "notes.p1":
      "Coloque uma peça em qualquer célula vazia, em qualquer rotação. Toda seta apontando para um vizinho ocupado <b>vira</b> aquela peça para a sua cor. Viradas nunca encadeiam.",
    "notes.p2":
      "Virar é alternar, então uma seta apontada para uma peça <em>sua</em> entrega ela ao adversário. O tabuleiro mostra essas em vermelho.",
    "notes.p3":
      "Todas as células se enchem e vence quem mostrar mais da sua cor. O número de células é ímpar, então empate é impossível.",

    /* -- footer ------------------------------------------------------------ */
    "footer.engine": "Motor, solver e agentes rodam sem modificação sob Pyodide.",
  },

  en: {
    /* -- document ---------------------------------------------------------- */
    "html.lang": "en",
    "meta.description":
      "Play FLIPHEX in the browser. The rules run on the same Python engine that produced the project's exact solutions.",
    "skip.link": "Skip to content",
    "nav.toggle": "Toggle navigation",

    /* -- controls ---------------------------------------------------------- */
    "label.board": "Board",
    "board.5x5": "5×5 — the shipped game",
    "board.5x3": "5×3 — solved exactly",
    "board.3x3": "3×3 — solved exactly",
    "label.side": "You play",
    "side.purple": "purple — moves first",
    "side.green": "green — moves second",
    "label.opponent": "Against",
    "button.newGame": "New game",
    "lang.group": "Language",
    "lang.pt": "Ler em português",
    "lang.en": "Read in English",

    /* -- seats ------------------------------------------------------------- */
    "seat.human": "a second player",
    "seat.random": "the random agent",
    "seat.heuristic": "the heuristic agent",
    "seat.solver": "the exact solver",

    "origin.local": "Local checkout — every seat is offered, on every board.",
    "origin.solverHere":
      "The solver plays this board perfectly. It needs about 8 s for the opening.",
    "origin.solverElsewhere":
      "The exact solver is offered on the 3×3, where it plays perfectly from the first move.",

    /* -- board and boot ---------------------------------------------------- */
    "board.aria": "FLIPHEX board",
    "boot.engine": "Starting the rules engine…",
    "boot.note":
      "This board is real; it is not playable until the engine starts. The page runs the project's actual Python, compiled to WebAssembly — the rules are never reimplemented in JavaScript.",
    "boot.runtime": "Downloading the Python runtime…",
    "boot.unpack": "Unpacking the engine…",
    "boot.rules": "Starting the rules…",
    "boot.failed": "The engine did not start.",

    "badge.booting": "booting",
    "badge.ready": "ready",
    "badge.readyIn": "ready in {seconds}s",
    "badge.failed": "failed",

    /* -- colours ----------------------------------------------------------- */
    "colour.PURPLE": "Purple",
    "colour.GREEN": "Green",
    "colour.purple": "purple",
    "colour.green": "green",

    /* -- panels ------------------------------------------------------------ */
    "panel.hand": "Your pieces",
    "button.undo": "Undo",
    "panel.rotation": "Rotation",
    "button.cancel": "Cancel",
    "hint.net": "Hover to preview. <b>Net</b> is tiles gained minus tiles handed back.",
    "hand.title": "{colour} — {count} left",
    "piece.title": "{archetype} — {arrows} arrow(s), {rotations} distinct rotation(s)",

    /* -- status ------------------------------------------------------------ */
    "turn.toMove": "{colour} to move",
    "turn.wins": "{colour} wins",

    "hint.pick": "Pick a piece, then a cell.",
    "hint.thinking": "The agent is thinking…",
    "hint.cell": "Now pick a highlighted cell.",
    "hint.rotation": "Choose a rotation.",
    "hint.tapAgain": "Tap it again to place, or pick another rotation.",
    "hint.tapPreview": "Tap a rotation to preview it, then tap again to place.",
    "hint.searching": "Searching — the page is frozen until the solver replies.",
    "hint.full": "The board is full. {cells} is odd, so there is never a draw.",

    /* -- commentary -------------------------------------------------------- */
    "say.searching":
      "<b>The solver is searching.</b> It runs on the page's only thread, so the tab will not respond until it answers.",
    "say.played": "<b>{who}</b> played <b>{archetype}</b> on <b>{cell}</b>",
    "say.flipping": "flipping {count}",
    "say.handingBack": "handing back {count}",
    "say.nothing": "with nothing to flip",
    "say.hotseat": "Hotseat — both colours are yours.",
    "say.standing": "You hold <b>{held}</b>, against <b>{seat}</b>. The position stands.",
    "say.withdrawn": "This board does not offer {gone}, so you are playing <b>{now}</b>.",

    /* -- rules summary ----------------------------------------------------- */
    "notes.summary": "How it works",
    "notes.p1":
      "Place a tile on any empty cell at any rotation. Every arrow pointing at an occupied neighbour <b>flips</b> it to your colour. Flips never chain.",
    "notes.p2":
      "A flip is a toggle, so an arrow aimed at <em>your own</em> tile hands it to your opponent. The board shows those in red.",
    "notes.p3":
      "All cells fill and whoever shows more of their colour wins. The cell count is odd, so a draw is impossible.",

    /* -- footer ------------------------------------------------------------ */
    "footer.engine": "Engine, solver and agents run unmodified under Pyodide.",
  },
};

let current = DEFAULT_LANG;

export function getLang() {
  return current;
}

/* What the visitor chose last time, or null.
 *
 * Deliberately *not* `navigator.language`. Portuguese is the default because of
 * the exhibition, not because of a guess about the browser — and a page that
 * silently picks a language from a setting the visitor never made for this site
 * is harder to reason about than one with a stated default and a visible
 * switch. The stored value is a choice somebody actually made here. */
export function storedLang() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return LANGS.includes(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function setLang(lang, doc = globalThis.document) {
  current = LANGS.includes(lang) ? lang : DEFAULT_LANG;
  try {
    localStorage.setItem(STORAGE_KEY, current);
  } catch {
    /* no storage: the choice holds for this page and is forgotten on reload */
  }
  if (doc?.documentElement) {
    // Screen readers choose a voice from this, and search engines index by it.
    // A page that swaps its words and keeps `lang="pt-BR"` is read aloud in the
    // wrong accent, which is a worse failure than the one it looks like.
    doc.documentElement.lang = t("html.lang");
  }
  return current;
}

/* Look up `key` and substitute `{name}` placeholders from `vars`.
 *
 * A placeholder with no matching variable is left in place rather than blanked,
 * for the same reason a missing key returns itself: a visible defect gets
 * fixed and an invisible one ships. */
export function t(key, vars) {
  const table = STRINGS[current] ?? STRINGS[DEFAULT_LANG];
  const template = table[key];
  if (template === undefined) return key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name) =>
    name in vars ? String(vars[name]) : whole,
  );
}

/* Rewrite everything in the markup that carries a key.
 *
 *   data-i18n="key"                 replaces textContent
 *   data-i18n-html="key"            replaces innerHTML, for copy with <b>/<em>
 *   data-i18n-attr="aria-label:key" replaces an attribute; several are
 *                                   separated by commas
 *
 * Content is authored in `index.html` and duplicated in the dictionaries above,
 * which is a real cost: the Portuguese lives in two places and they can drift.
 * The alternative is an empty page that fills in after the module loads, and an
 * interface whose default rendering depends on JavaScript having run is worse
 * than one whose translation does. `test/page.test.mjs` asserts that every key
 * named in the markup exists in both dictionaries. */
export function applyStatic(root = globalThis.document) {
  if (!root?.querySelectorAll) return;

  for (const node of root.querySelectorAll("[data-i18n]")) {
    node.textContent = t(node.dataset.i18n);
  }
  for (const node of root.querySelectorAll("[data-i18n-html]")) {
    node.innerHTML = t(node.dataset.i18nHtml);
  }
  for (const node of root.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of node.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((part) => part.trim());
      if (attr && key) node.setAttribute(attr, t(key));
    }
  }
}
