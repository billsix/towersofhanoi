// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Towers of Hanoi — Tauri frontend. Plain vanilla JS (no bundler); uses the
// global Tauri API (`app.withGlobalTauri` in tauri.conf.json). Every backend
// command returns the same Snapshot, which render() paints. The game logic
// lives entirely in the Rust `hanoigame` crate behind the commands.
//
// The UI follows the three-tier learning flow (feature-spec.md §3.5, realized in
// the wxPython oracle): Tier 1 is always visible (board, goal line, move history,
// feedback, How-to-Play); Tier 2 (relabelling, saving/recipes) unlocks at the
// first win; Tier 3 keeps relabelling and recipes on the menu bar, out of the
// always-visible workspace.
// @ts-check

// --- IPC view-models: the serde shapes the Rust `#[tauri::command]`s return
// (src-tauri/src/main.rs). Field names are serde's snake_case; Rust `Option<T>`
// serialises to `T | null`. These are the one-serde-view boundary. -------------

/**
 * One saved recipe's summary (Rust `RecipeInfo`).
 * @typedef {object} RecipeInfo
 * @property {string} name
 * @property {number} disks
 * @property {number} moves
 */

/**
 * The on-invoke three-panel rebinding view (Rust `ApplyView`, feature-spec §4.8):
 * the recipe's own moves | the label→peg rebinding | the rebound physical moves.
 * `relabelled` gates the panel.
 * @typedef {object} ApplyView
 * @property {string} name
 * @property {boolean} relabelled
 * @property {[number, number][]} recipe_moves
 * @property {[number, number][]} rebinding
 * @property {[number, number][]} rebound_moves
 */

/**
 * The whole game state every command returns (Rust `Snapshot`). `apply` is
 * populated only by `apply_recipe`, `null` otherwise.
 * @typedef {object} Snapshot
 * @property {string[]} board
 * @property {number[][]} towers
 * @property {number} num_disks
 * @property {number} moves
 * @property {number} min_moves
 * @property {[number, number, number]} labels
 * @property {[number, number][]} legal
 * @property {boolean} won
 * @property {[number, number][]} rebinding
 * @property {RecipeInfo[]} recipes
 * @property {[number, number][]} history
 * @property {string} message
 * @property {ApplyView|null} apply
 */

// `globalThis.__TAURI__` is injected at runtime by Tauri's `withGlobalTauri` (in the
// webview `globalThis === window`); it has no static type, so reach it through an `any`
// cast, give `invoke` an explicit signature, and cast each call's result to the
// Snapshot / string[] it returns.
/** @type {(cmd: string, args?: Record<string, unknown>) => Promise<unknown>} */
const invoke = /** @type {any} */ (globalThis).__TAURI__.core.invoke;

/** @type {[number, number][]} */
const MOVE_PAIRS = [[1, 2], [1, 3], [2, 1], [2, 3], [3, 1], [3, 2]];
/** @type {[number, number, number][]} */
const RELABEL_PERMS = [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [
  3,
  2,
  1,
]];

// Tier-2 latch: once the player has won at least once this session, the Relabel
// and Recipe menus stay unlocked (dim-don't-remove; feature-spec §3.5).
let wonOnce = false;
// The latest snapshot, so menu actions (Save) can read e.g. the disc count.
/** @type {Snapshot|null} */
let latest = null;

// Disc drag-drop (spike, mirrored across the GUIs): the physical peg (0,1,2)
// whose top disc is being dragged (null = none), its size, and the pointer
// position on the canvas.
/** @type {number|null} */
let dragSrc = null;
let dragSize = 0;
let dragX = 0;
let dragY = 0;

/**
 * The three peg-centre x-coordinates on a `w`-wide canvas. Shared by the board
 * drawing and the drag hit-test so they agree on where the pegs are.
 * @param {number} w
 * @returns {number[]}
 */
function boardPegCentres(w) {
  const margin = 20;
  const availW = Math.max(w - 2 * margin, 80);
  const pegZoneW = availW / 3;
  return [0, 1, 2].map((i) => margin + pegZoneW * (i + 0.5));
}

/**
 * The physical peg (0,1,2) whose centre is nearest `x` on a `w`-wide canvas --
 * forgiving drop targeting.
 * @param {number} x
 * @param {number} w
 * @returns {number}
 */
function nearestPeg(x, w) {
  const c = boardPegCentres(w);
  let best = 0;
  for (let i = 1; i < 3; i++) {
    if (Math.abs(x - c[i]) < Math.abs(x - c[best])) best = i;
  }
  return best;
}

// --- Graphics board (a <canvas> mirror of the wxDragon DC board; same palettes,
// disc-width curve and layout as rust/hanoi-gui/src/main.rs::draw_board_dc) -----

// Disc colour by size (1-indexed); cycles past 10 discs.
/** @type {[number, number, number][]} */
const DISC_RGB = [
  [232, 80, 80],
  [232, 145, 70],
  [235, 200, 75],
  [170, 210, 80],
  [85, 195, 130],
  [75, 170, 220],
  [100, 130, 220],
  [160, 110, 220],
  [220, 110, 200],
  [185, 145, 110],
];
// Label-badge colour by 0-indexed label (blue / yellow / red).
/** @type {[number, number, number][]} */
const LABEL_RGB = [[70, 130, 200], [230, 195, 70], [220, 90, 80]];

/** @type {(c: [number, number, number]) => string} */
const rgb = ([r, g, b]) => `rgb(${r},${g},${b})`;
/** @type {(c: [number, number, number], amt: number) => string} */
const darken = ([r, g, b], amt) =>
  `rgb(${Math.floor(r * (1 - amt))},${Math.floor(g * (1 - amt))},${
    Math.floor(b * (1 - amt))
  })`;

/** @param {string} id @returns {HTMLElement} */
function el(id) {
  return /** @type {HTMLElement} */ (document.getElementById(id));
}

/**
 * Width of a disc of `size` in an `n`-disc game, up to `maxW` (smallest is 1/3 the
 * largest — a visible difference without being tiny).
 * @param {number} size
 * @param {number} n
 * @param {number} maxW
 * @returns {number}
 */
function discWidth(size, n, maxW) {
  if (n <= 1) return maxW;
  const smallest = maxW / 3;
  return smallest + (maxW - smallest) * (size - 1) / (n - 1);
}

/**
 * Filled + stroked rounded rectangle on the 2D context.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x
 * @param {number} y
 * @param {number} w
 * @param {number} h
 * @param {number} r
 * @returns {void}
 */
function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, radius);
  ctx.fill();
  ctx.stroke();
}

/**
 * Paint the <canvas> board from a snapshot: base bar, pegs, size-coloured discs,
 * and the active label badges (+ the 1-2-3 reference row when relabelled).
 * @param {Snapshot} s
 * @returns {void}
 */
function drawBoard(s) {
  const canvas =
    /** @type {HTMLCanvasElement} */ (document.getElementById("canvas"));
  const ctx = /** @type {CanvasRenderingContext2D} */ (canvas.getContext("2d"));
  const w = canvas.width;
  const h = canvas.height;

  ctx.fillStyle = "rgb(30,36,50)";
  ctx.fillRect(0, 0, w, h);

  const n = s.num_disks;
  if (n === 0) return;
  const relabelled = s.rebinding.length > 0;

  const margin = 20;
  const labelBandH = relabelled ? 60 : 36;
  const baseH = 14;
  const availW = Math.max(w - 2 * margin, 80);
  const availH = Math.max(h - 2 * margin - labelBandH - baseH, 80);
  const pegZoneW = availW / 3;
  const discH = Math.min((availH / Math.max(n, 4)) * 0.92, 30);
  const maxDiscW = pegZoneW * 0.92;
  const pegW = Math.max(maxDiscW * 0.07, 8);
  const pegH = availH * 0.95;
  const baseY = h - margin - labelBandH - baseH;
  const pegTopY = baseY - pegH;
  const pegCentres = boardPegCentres(w);

  ctx.lineWidth = 1;

  // Base bar.
  ctx.strokeStyle = "rgb(90,64,38)";
  ctx.fillStyle = "rgb(150,110,70)";
  roundRect(ctx, margin, baseY, w - 2 * margin, baseH, 4);

  // Pegs.
  ctx.strokeStyle = "rgb(120,86,50)";
  ctx.fillStyle = "rgb(160,120,75)";
  for (const cx of pegCentres) {
    roundRect(ctx, cx - pegW / 2, pegTopY, pegW, pegH, pegW / 2);
  }

  // Discs (bottom-up), coloured by size.
  s.towers.forEach((stack, p) => {
    const cx = pegCentres[p];
    stack.forEach((size, idx) => {
      // Omit the disc currently being dragged from its home peg.
      if (p === dragSrc && idx === stack.length - 1) return;
      const dw = discWidth(size, n, maxDiscW);
      const y = baseY - (idx + 1) * discH * 1.04;
      const colour = DISC_RGB[(size - 1) % DISC_RGB.length];
      ctx.strokeStyle = darken(colour, 0.45);
      ctx.fillStyle = rgb(colour);
      roundRect(ctx, cx - dw / 2, y, dw, discH, discH / 3);
    });
  });

  // Active label badges (coloured circles with the label digit).
  const activeLabelY = baseY + baseH + (relabelled ? 18 : labelBandH / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "13px system-ui, sans-serif";
  pegCentres.forEach((cx, p) => {
    const label = s.labels[p];
    const colour = LABEL_RGB[(label - 1) % LABEL_RGB.length];
    ctx.strokeStyle = darken(colour, 0.4);
    ctx.fillStyle = rgb(colour);
    ctx.beginPath();
    ctx.arc(cx, activeLabelY, 14, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "rgb(255,255,255)";
    ctx.fillText(String(label), cx, activeLabelY);
  });

  // Default 1-2-3 reference row when relabelled (the physical peg numbers).
  if (relabelled) {
    ctx.fillStyle = "rgb(170,178,195)";
    pegCentres.forEach((cx, p) =>
      ctx.fillText(String(p + 1), cx, activeLabelY + 26)
    );
  }

  // The dragged disc follows the pointer, drawn on top in its size colour.
  if (dragSrc !== null) {
    const dw = discWidth(dragSize, n, maxDiscW);
    const colour = DISC_RGB[(dragSize - 1) % DISC_RGB.length];
    ctx.strokeStyle = darken(colour, 0.45);
    ctx.fillStyle = rgb(colour);
    roundRect(ctx, dragX - dw / 2, dragY - discH / 2, dw, discH, discH / 3);
  }
}

/**
 * Fill the Relabel menu: one item per permutation, the active labelling marked,
 * all disabled while the current game is already solved.
 * @param {Snapshot} s
 * @returns {void}
 */
function renderRelabelMenu(s) {
  /** @type {(perm: number[]) => boolean} */
  const isActive = (perm) =>
    perm[0] === s.labels[0] && perm[1] === s.labels[1] &&
    perm[2] === s.labels[2];
  el("relabel-panel").innerHTML = RELABEL_PERMS.map((perm) =>
    `<button class="menu-item" data-perm="${perm.join("")}"${
      s.won ? " disabled" : ""
    }>${isActive(perm) ? "● " : "○ "}${perm.join(" ")}</button>`
  ).join("");
}

/**
 * Fill the Recipe menu: Save current solution (enabled only at a win), then each
 * saved recipe as a row with View / Apply (Apply disabled once the game is solved).
 * @param {Snapshot} s
 * @returns {void}
 */
function renderRecipeMenu(s) {
  const save = `<button class="menu-item" data-act="save"${
    s.won ? "" : " disabled"
  }>Save current solution</button><hr />`;
  const body = s.recipes.length === 0
    ? `<span class="menu-empty">(no saved recipes yet)</span>`
    : s.recipes.map((r) =>
      `<div class="recipe-row"><span>${r.name} (${r.disks} discs, ${r.moves} moves)</span>` +
      `<button class="menu-item" data-act="view" data-name="${r.name}">View</button>` +
      `<button class="menu-item" data-act="apply" data-name="${r.name}"${
        s.won ? " disabled" : ""
      }>Apply</button></div>`
    ).join("");
  el("recipe-panel").innerHTML = save + body;
}

/**
 * Paint the whole UI from a snapshot: board, goal line, message, history, the
 * move buttons' enabled state, the Tier-2 menu gating, the menus, and the apply view.
 * @param {Snapshot} s
 * @returns {void}
 */
function render(s) {
  latest = s;
  wonOnce = wonOnce || s.won;

  drawBoard(s);
  el("board").textContent = s.board.join("\n");

  // Tier-1 goal line (always visible).
  el("status").textContent =
    `Goal: move all ${s.num_disks} discs to peg 3    ` +
    `Moves: ${s.moves} / optimal ${s.min_moves}    Labelling: ${
      s.labels.join(" ")
    }`;

  let message = s.message || "";
  if (s.won && !message) {
    const verdict = s.moves === s.min_moves
      ? "Optimal!"
      : `${s.moves - s.min_moves} more than the minimum (${s.min_moves}).`;
    message =
      `Solved in ${s.moves} moves — ${verdict}  Save it from the Recipe menu to keep it.`;
  }
  el("message").textContent = message;

  el("rebinding").textContent = s.rebinding.length
    ? "Rebinding: " +
      s.rebinding.map(([l, p]) => `label ${l} → peg ${p}`).join(",   ")
    : "";

  // Tier-1 move history (always visible): the running default-label tally.
  const hist = el("history");
  hist.classList.toggle("empty", s.history.length === 0);
  hist.innerHTML = s.history.length === 0
    ? `<li class="muted">(no moves yet)</li>`
    : s.history.map(([a, b]) => `<li>${a} -&gt; ${b}</li>`).join("");

  /** @type {Set<string>} */
  const legal = new Set(s.legal.map(([f, t]) => `${f}-${t}`));
  for (const [f, t] of MOVE_PAIRS) {
    /** @type {HTMLButtonElement} */ (el(`move-${f}-${t}`)).disabled = s.won ||
      !legal.has(`${f}-${t}`);
  }

  // Tier-2 gating: the Relabel and Recipe menus unlock at the first win.
  /** @type {HTMLButtonElement} */ (el("relabel-btn")).disabled = !wonOnce;
  /** @type {HTMLButtonElement} */ (el("recipe-btn")).disabled = !wonOnce;
  renderRelabelMenu(s);
  renderRecipeMenu(s);

  renderApplyView(s.apply);
}

/**
 * The on-invoke three-panel rebinding view (feature-spec §4.8): the recipe's own
 * moves | the label→peg rebinding | the rebound physical moves, plus the per-step
 * replay log. Shown only under a non-default labelling (nothing to teach otherwise).
 * @param {ApplyView|null} apply
 * @returns {void}
 */
function renderApplyView(apply) {
  const panel = el("apply-view");
  if (!apply || !apply.relabelled) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }
  /** @type {(title: string, rows: string[]) => string} */
  const col = (title, rows) =>
    `<div class="apply-col"><h4>${title}</h4>${
      rows.map((r) => `<div>${r}</div>`).join("")
    }</div>`;
  const recipeCol = apply.recipe_moves.map(([a, b], i) =>
    `${i + 1}: ${a} → ${b}`
  );
  const rebindCol = apply.rebinding.map(([l, p]) => `label ${l} → peg ${p}`);
  const reboundCol = apply.rebound_moves.map(([a, b], i) =>
    `${i + 1}: ${a} → ${b}`
  );
  panel.innerHTML =
    `<h3>Applying &lsquo;${apply.name}&rsquo; under your relabelling</h3>` +
    `<div class="apply-cols">` +
    col("Recipe (its labels)", recipeCol) +
    col("Rebinding (label &rarr; peg)", rebindCol) +
    col("Rebound (physical pegs)", reboundCol) +
    `</div>`;
  panel.classList.remove("hidden");
}

/** Close every open menu-bar dropdown. @returns {void} */
function closeMenus() {
  document.querySelectorAll(".menu.open").forEach((m) =>
    m.classList.remove("open")
  );
}

/**
 * Wire the menu bar: a click on an (enabled) menu button toggles its dropdown and
 * closes the others; a click anywhere else closes them; clicks inside a panel stay
 * open unless an action closes the menu explicitly.
 * @returns {void}
 */
function initMenuBar() {
  document.querySelectorAll(".menu-btn").forEach((b) =>
    b.addEventListener("click", (e) => {
      const btn = /** @type {HTMLButtonElement} */ (e.currentTarget);
      if (btn.disabled) return;
      const menu = /** @type {HTMLElement} */ (btn.parentElement);
      const willOpen = !menu.classList.contains("open");
      closeMenus();
      if (willOpen) menu.classList.add("open");
      e.stopPropagation();
    })
  );
  // Clicks inside a panel do not bubble to the document closer; actions close
  // the menu themselves.
  document.querySelectorAll(".menu-panel").forEach((p) =>
    p.addEventListener("click", (e) => e.stopPropagation())
  );
  document.addEventListener("click", closeMenus);
}

/**
 * Wire every control to its backend command and paint the initial snapshot.
 * @returns {Promise<void>}
 */
/**
 * Wire disc drag-drop on the <canvas> board (spike, mirrored across the GUIs):
 * press picks up the top disc of the nearest peg, pointer moves it, release
 * drops on the nearest peg and dispatches `do_move` (which validates + reports
 * an illegal drop). Pointer capture keeps the drag alive outside the canvas;
 * dragging is off once won. The move buttons stay as the accessible path.
 * @returns {void}
 */
function initBoardDrag() {
  const canvas =
    /** @type {HTMLCanvasElement} */ (document.getElementById("canvas"));
  /**
   * @param {PointerEvent} e
   * @returns {{ x: number; y: number }}
   */
  const canvasPos = (e) => {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (canvas.width / rect.width),
      y: (e.clientY - rect.top) * (canvas.height / rect.height),
    };
  };
  canvas.addEventListener("pointerdown", (e) => {
    if (!latest || latest.won) return;
    const { x, y } = canvasPos(e);
    const peg = nearestPeg(x, canvas.width);
    const stack = latest.towers[peg];
    if (!stack || stack.length === 0) return;
    dragSrc = peg;
    dragSize = stack[stack.length - 1];
    dragX = x;
    dragY = y;
    canvas.setPointerCapture(e.pointerId);
    drawBoard(latest);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (dragSrc === null || !latest) return;
    const p = canvasPos(e);
    dragX = p.x;
    dragY = p.y;
    drawBoard(latest);
  });
  canvas.addEventListener("pointerup", async (e) => {
    if (dragSrc === null || !latest) return;
    const src = dragSrc;
    const target = nearestPeg(canvasPos(e).x, canvas.width);
    dragSrc = null;
    drawBoard(latest); // snap back to the true board state
    if (target !== src) {
      const from = latest.labels[src];
      const to = latest.labels[target];
      render(/** @type {Snapshot} */ (await invoke("do_move", { from, to })));
    }
  });
  canvas.addEventListener("pointercancel", () => {
    dragSrc = null;
    if (latest) drawBoard(latest);
  });
}

async function init() {
  initMenuBar();
  initBoardDrag();

  for (const [f, t] of MOVE_PAIRS) {
    el(`move-${f}-${t}`).addEventListener("click", async () => {
      render(
        /** @type {Snapshot} */ (await invoke("do_move", { from: f, to: t })),
      );
    });
  }

  // Relabel menu (delegated: the items are re-rendered each snapshot).
  el("relabel-panel").addEventListener("click", async (e) => {
    const target = /** @type {HTMLElement} */ (e.target);
    const raw = target.dataset ? target.dataset.perm : undefined;
    if (!raw) return;
    /** @type {[number, number, number]} */
    const labels = [Number(raw[0]), Number(raw[1]), Number(raw[2])];
    closeMenus();
    render(/** @type {Snapshot} */ (await invoke("relabel", { labels })));
  });

  // Recipe menu (delegated): Save current solution / per-recipe View / Apply.
  el("recipe-panel").addEventListener("click", async (e) => {
    const target = /** @type {HTMLElement} */ (e.target);
    const act = target.dataset ? target.dataset.act : undefined;
    if (!act) return;
    const name = target.dataset.name;
    closeMenus();
    if (act === "save") {
      const discs = latest ? latest.num_disks : 3;
      render(
        /** @type {Snapshot} */ (await invoke("save_recipe", {
          name: `solve-${discs}`,
        })),
      );
    } else if (act === "view" && name) {
      const steps = /** @type {string[]} */ (await invoke("show_recipe", {
        name,
      }));
      alert(steps.join("\n"));
    } else if (act === "apply" && name) {
      render(/** @type {Snapshot} */ (await invoke("apply_recipe", { name })));
    }
  });

  el("newgame").addEventListener("click", async () => {
    const discs = parseInt(
      /** @type {HTMLInputElement} */ (el("discs")).value,
      10,
    ) || 3;
    closeMenus();
    render(/** @type {Snapshot} */ (await invoke("new_game", { discs })));
  });

  // How-to-Play dialog: opens from the Help menu, and once automatically on first run.
  const dialog = /** @type {HTMLDialogElement} */ (el("howto-dialog"));
  el("howto").addEventListener("click", () => {
    closeMenus();
    dialog.showModal();
  });

  // Text / Graphics board toggle (the graphics canvas is the default view, as in
  // the wxDragon GUI; the monospace text board is one click away).
  el("toggle-view").addEventListener("click", (e) => {
    const canvas =
      /** @type {HTMLCanvasElement} */ (document.getElementById("canvas"));
    const text = el("board");
    const btn = /** @type {HTMLElement} */ (e.target);
    const showText = canvas.classList.toggle("hidden");
    text.classList.toggle("hidden", !showText);
    btn.textContent = showText ? "Graphics view" : "Text view";
  });

  render(/** @type {Snapshot} */ (await invoke("snapshot")));
  dialog.showModal();
}

globalThis.addEventListener("DOMContentLoaded", init);
