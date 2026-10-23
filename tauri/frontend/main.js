// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Towers of Hanoi — Tauri frontend. Plain vanilla JS (no bundler); uses the
// global Tauri API (`app.withGlobalTauri` in tauri.conf.json). Every backend
// command returns the same Snapshot, which render() paints. The game logic
// lives entirely in the Rust `hanoigame` crate behind the commands.

const { invoke } = window.__TAURI__.core;

const MOVE_PAIRS = [[1, 2], [1, 3], [2, 1], [2, 3], [3, 1], [3, 2]];
const RELABEL_PERMS = [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]];

// --- Graphics board (a <canvas> mirror of the wxDragon DC board; same palettes,
// disc-width curve and layout as rust/hanoi-gui/src/main.rs::draw_board_dc) -----

// Disc colour by size (1-indexed); cycles past 10 discs.
const DISC_RGB = [
  [232, 80, 80], [232, 145, 70], [235, 200, 75], [170, 210, 80], [85, 195, 130],
  [75, 170, 220], [100, 130, 220], [160, 110, 220], [220, 110, 200], [185, 145, 110],
];
// Label-badge colour by 0-indexed label (blue / yellow / red).
const LABEL_RGB = [[70, 130, 200], [230, 195, 70], [220, 90, 80]];

const rgb = ([r, g, b]) => `rgb(${r},${g},${b})`;
const darken = ([r, g, b], amt) =>
  `rgb(${Math.floor(r * (1 - amt))},${Math.floor(g * (1 - amt))},${Math.floor(b * (1 - amt))})`;

// Width of a disc of `size` in an `n`-disc game, up to `maxW` (smallest is 1/3 the
// largest — a visible difference without being tiny).
function discWidth(size, n, maxW) {
  if (n <= 1) return maxW;
  const smallest = maxW / 3;
  return smallest + (maxW - smallest) * (size - 1) / (n - 1);
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, radius);
  ctx.fill();
  ctx.stroke();
}

function drawBoard(s) {
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
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

function render(s) {
  drawBoard(s);
  document.getElementById("board").textContent = s.board.join("\n");
  document.getElementById("status").textContent =
    `Discs: ${s.num_disks}    Labelling: ${s.labels.join(" ")}    ` +
    `Moves: ${s.moves}    Recipes: ${s.recipes.length}`;

  let message = s.message || "";
  if (s.won && !message) {
    const verdict = s.moves === s.min_moves
      ? "Optimal!"
      : `${s.moves - s.min_moves} more than the minimum (${s.min_moves}).`;
    message = `Solved in ${s.moves} moves — ${verdict}  Save it below to keep it.`;
  }
  document.getElementById("message").textContent = message;

  document.getElementById("rebinding").textContent = s.rebinding.length
    ? "Rebinding: " + s.rebinding.map(([l, p]) => `label ${l} → peg ${p}`).join(",   ")
    : "";

  const legal = new Set(s.legal.map(([f, t]) => `${f}-${t}`));
  for (const [f, t] of MOVE_PAIRS) {
    document.getElementById(`move-${f}-${t}`).disabled = s.won || !legal.has(`${f}-${t}`);
  }

  const sel = document.getElementById("recipes");
  const previous = sel.value;
  sel.innerHTML = "";
  for (const r of s.recipes) {
    const opt = document.createElement("option");
    opt.value = r.name;
    opt.textContent = `${r.name}  (${r.disks} discs, ${r.moves} moves)`;
    sel.appendChild(opt);
  }
  if (previous) sel.value = previous;

  document.getElementById("save").disabled = !s.won;
  document.getElementById("savename").placeholder = `solve-${s.num_disks}`;
}

async function init() {
  for (const [f, t] of MOVE_PAIRS) {
    document.getElementById(`move-${f}-${t}`).addEventListener("click", async () => {
      render(await invoke("do_move", { from: f, to: t }));
    });
  }
  for (const perm of RELABEL_PERMS) {
    document.getElementById(`relabel-${perm.join("")}`).addEventListener("click", async () => {
      render(await invoke("relabel", { labels: perm }));
    });
  }
  document.getElementById("newgame").addEventListener("click", async () => {
    const discs = parseInt(document.getElementById("discs").value, 10) || 3;
    render(await invoke("new_game", { discs }));
  });
  document.getElementById("save").addEventListener("click", async () => {
    const name = document.getElementById("savename").value.trim();
    render(await invoke("save_recipe", { name }));
    document.getElementById("savename").value = "";
  });
  document.getElementById("apply").addEventListener("click", async () => {
    const name = document.getElementById("recipes").value;
    if (name) render(await invoke("apply_recipe", { name }));
  });
  document.getElementById("show").addEventListener("click", async () => {
    const name = document.getElementById("recipes").value;
    if (name) {
      const steps = await invoke("show_recipe", { name });
      alert(steps.join("\n"));
    }
  });

  // Text / Graphics board toggle (the graphics canvas is the default view, as in
  // the wxDragon GUI; the monospace text board is one click away).
  document.getElementById("toggle-view").addEventListener("click", (e) => {
    const canvas = document.getElementById("canvas");
    const text = document.getElementById("board");
    const showText = canvas.classList.toggle("hidden");
    text.classList.toggle("hidden", !showText);
    e.target.textContent = showText ? "Graphics view" : "Text view";
  });

  render(await invoke("snapshot"));
}

window.addEventListener("DOMContentLoaded", init);
