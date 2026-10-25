// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Towers of Hanoi — Tauri frontend. Plain vanilla JS (no bundler); uses the
// global Tauri API (`app.withGlobalTauri` in tauri.conf.json). Every backend
// command returns the same Snapshot, which render() paints. The game logic
// lives entirely in the Rust `hanoigame` crate behind the commands.
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
 * One replayed step of an applied recipe (Rust `ApplyStep`); `*_peg`/`error` are
 * `null` when unresolved / when the step applied.
 * @typedef {object} ApplyStep
 * @property {number} from_label
 * @property {number} to_label
 * @property {number|null} from_peg
 * @property {number|null} to_peg
 * @property {string|null} error
 */

/**
 * The on-invoke three-panel rebinding view (Rust `ApplyView`, feature-spec §4.8):
 * the recipe's own moves | the label→peg rebinding | the rebound physical moves,
 * plus the per-step replay log. `relabelled` gates the panel.
 * @typedef {object} ApplyView
 * @property {string} name
 * @property {boolean} relabelled
 * @property {[number, number][]} recipe_moves
 * @property {[number, number][]} rebinding
 * @property {[number, number][]} rebound_moves
 * @property {ApplyStep[]} steps
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
const RELABEL_PERMS = [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]];

/** @type {string} */
const HELP_TEXT = [
  "Towers of Hanoi — move every disc to the third peg, never a larger disc onto a smaller one.",
  "",
  "Move: click a 'from → to' button (in the current labels); illegal moves are disabled.",
  "Relabel: rename the physical pegs (a permutation of 1,2,3). Discs don't move, and colours track",
  "  the label — so a solved sub-problem can be replayed under a new name.",
  "Recipes: after you win, Save the solution (default name solve-N). Apply replays a saved recipe",
  "  under the current labelling and, when relabelled, shows the three-panel rebinding (the recipe's",
  "  labels | label → peg | the rebound moves on the physical pegs). Show lists a recipe's moves.",
  "New Game: pick a disc count (1–10).",
].join("\n");

// --- Graphics board (a <canvas> mirror of the wxDragon DC board; same palettes,
// disc-width curve and layout as rust/hanoi-gui/src/main.rs::draw_board_dc) -----

// Disc colour by size (1-indexed); cycles past 10 discs.
/** @type {[number, number, number][]} */
const DISC_RGB = [
  [232, 80, 80], [232, 145, 70], [235, 200, 75], [170, 210, 80], [85, 195, 130],
  [75, 170, 220], [100, 130, 220], [160, 110, 220], [220, 110, 200], [185, 145, 110],
];
// Label-badge colour by 0-indexed label (blue / yellow / red).
/** @type {[number, number, number][]} */
const LABEL_RGB = [[70, 130, 200], [230, 195, 70], [220, 90, 80]];

/** @type {(c: [number, number, number]) => string} */
const rgb = ([r, g, b]) => `rgb(${r},${g},${b})`;
/** @type {(c: [number, number, number], amt: number) => string} */
const darken = ([r, g, b], amt) =>
  `rgb(${Math.floor(r * (1 - amt))},${Math.floor(g * (1 - amt))},${Math.floor(b * (1 - amt))})`;

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
  const canvas = /** @type {HTMLCanvasElement} */ (document.getElementById("canvas"));
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
  /** @type {number[]} */
  const pegCentres = [0, 1, 2].map((i) => margin + pegZoneW * (i + 0.5));

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
    pegCentres.forEach((cx, p) => ctx.fillText(String(p + 1), cx, activeLabelY + 26));
  }
}

/**
 * Paint the whole UI from a snapshot: board, status, message, rebinding line, the
 * move buttons' enabled state, the recipe list, the save control, and the apply view.
 * @param {Snapshot} s
 * @returns {void}
 */
function render(s) {
  drawBoard(s);
  /** @type {HTMLElement} */ (document.getElementById("board")).textContent = s.board.join("\n");
  /** @type {HTMLElement} */ (document.getElementById("status")).textContent =
    `Discs: ${s.num_disks}    Labelling: ${s.labels.join(" ")}    ` +
    `Moves: ${s.moves}    Recipes: ${s.recipes.length}`;

  let message = s.message || "";
  if (s.won && !message) {
    const verdict = s.moves === s.min_moves
      ? "Optimal!"
      : `${s.moves - s.min_moves} more than the minimum (${s.min_moves}).`;
    message = `Solved in ${s.moves} moves — ${verdict}  Save it below to keep it.`;
  }
  /** @type {HTMLElement} */ (document.getElementById("message")).textContent = message;

  /** @type {HTMLElement} */ (document.getElementById("rebinding")).textContent = s.rebinding.length
    ? "Rebinding: " + s.rebinding.map(([l, p]) => `label ${l} → peg ${p}`).join(",   ")
    : "";

  /** @type {Set<string>} */
  const legal = new Set(s.legal.map(([f, t]) => `${f}-${t}`));
  for (const [f, t] of MOVE_PAIRS) {
    /** @type {HTMLButtonElement} */ (document.getElementById(`move-${f}-${t}`)).disabled =
      s.won || !legal.has(`${f}-${t}`);
  }

  const sel = /** @type {HTMLSelectElement} */ (document.getElementById("recipes"));
  const previous = sel.value;
  sel.innerHTML = "";
  for (const r of s.recipes) {
    const opt = document.createElement("option");
    opt.value = r.name;
    opt.textContent = `${r.name}  (${r.disks} discs, ${r.moves} moves)`;
    sel.appendChild(opt);
  }
  if (previous) sel.value = previous;

  /** @type {HTMLButtonElement} */ (document.getElementById("save")).disabled = !s.won;
  const sn = /** @type {HTMLInputElement} */ (document.getElementById("savename"));
  if (!sn.value) sn.value = `solve-${s.num_disks}`; // prefill the default name (feature-spec §4.5)

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
  const el = /** @type {HTMLElement} */ (document.getElementById("apply-view"));
  if (!apply || !apply.relabelled) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  /** @type {(title: string, rows: string[]) => string} */
  const col = (title, rows) =>
    `<div class="apply-col"><h4>${title}</h4>${rows.map((r) => `<div>${r}</div>`).join("")}</div>`;
  const recipeCol = apply.recipe_moves.map(([a, b], i) => `${i + 1}: ${a} → ${b}`);
  const rebindCol = apply.rebinding.map(([l, p]) => `label ${l} → peg ${p}`);
  const reboundCol = apply.rebound_moves.map(([a, b], i) => `${i + 1}: ${a} → ${b}`);
  const steps = apply.steps.map((st, i) =>
    st.error
      ? `step ${i + 1}: stopped — ${st.error}`
      : `step ${i + 1}: ${st.from_label} → ${st.to_label}`);
  el.innerHTML =
    `<h3>Applying &lsquo;${apply.name}&rsquo; under your relabelling</h3>` +
    `<div class="apply-cols">` +
    col("Recipe (its labels)", recipeCol) +
    col("Rebinding (label &rarr; peg)", rebindCol) +
    col("Rebound (physical pegs)", reboundCol) +
    `</div>` +
    `<div class="apply-steps"><h4>Steps</h4>${steps.map((r) => `<div>${r}</div>`).join("")}</div>`;
  el.classList.remove("hidden");
}

/**
 * Wire every control to its backend command and paint the initial snapshot.
 * @returns {Promise<void>}
 */
async function init() {
  for (const [f, t] of MOVE_PAIRS) {
    /** @type {HTMLElement} */ (document.getElementById(`move-${f}-${t}`)).addEventListener("click", async () => {
      render(/** @type {Snapshot} */ (await invoke("do_move", { from: f, to: t })));
    });
  }
  for (const perm of RELABEL_PERMS) {
    /** @type {HTMLElement} */ (document.getElementById(`relabel-${perm.join("")}`)).addEventListener("click", async () => {
      render(/** @type {Snapshot} */ (await invoke("relabel", { labels: perm })));
    });
  }
  /** @type {HTMLElement} */ (document.getElementById("newgame")).addEventListener("click", async () => {
    const discs = parseInt(/** @type {HTMLInputElement} */ (document.getElementById("discs")).value, 10) || 3;
    render(/** @type {Snapshot} */ (await invoke("new_game", { discs })));
  });
  /** @type {HTMLElement} */ (document.getElementById("save")).addEventListener("click", async () => {
    const sn = /** @type {HTMLInputElement} */ (document.getElementById("savename"));
    const s = /** @type {Snapshot} */ (await invoke("save_recipe", { name: sn.value.trim() }));
    render(s);
    sn.value = `solve-${s.num_disks}`; // reset to the default name for the next recipe
  });
  /** @type {HTMLElement} */ (document.getElementById("help")).addEventListener("click", () => alert(HELP_TEXT));
  /** @type {HTMLElement} */ (document.getElementById("apply")).addEventListener("click", async () => {
    const name = /** @type {HTMLSelectElement} */ (document.getElementById("recipes")).value;
    if (name) render(/** @type {Snapshot} */ (await invoke("apply_recipe", { name })));
  });
  /** @type {HTMLElement} */ (document.getElementById("show")).addEventListener("click", async () => {
    const name = /** @type {HTMLSelectElement} */ (document.getElementById("recipes")).value;
    if (name) {
      const steps = /** @type {string[]} */ (await invoke("show_recipe", { name }));
      alert(steps.join("\n"));
    }
  });

  // Text / Graphics board toggle (the graphics canvas is the default view, as in
  // the wxDragon GUI; the monospace text board is one click away).
  /** @type {HTMLElement} */ (document.getElementById("toggle-view")).addEventListener("click", (e) => {
    const canvas = /** @type {HTMLCanvasElement} */ (document.getElementById("canvas"));
    const text = /** @type {HTMLElement} */ (document.getElementById("board"));
    const btn = /** @type {HTMLElement} */ (e.target);
    const showText = canvas.classList.toggle("hidden");
    text.classList.toggle("hidden", !showText);
    btn.textContent = showText ? "Graphics view" : "Text view";
  });

  render(/** @type {Snapshot} */ (await invoke("snapshot")));
}

globalThis.addEventListener("DOMContentLoaded", init);
