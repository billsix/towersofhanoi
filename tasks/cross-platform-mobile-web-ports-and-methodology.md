# Cross-platform ports (Android / iPhone / iPad / Go web server) + extract the product-dev methodology

**Status:** blocked
**Blocked on:** (1) the desktop/web spec-parity foundation landing — the C++ parity
(`tasks/cpp-add-wx-frontend-and-recipe-view-parity.md`) and Rust parity
(`tasks/rust-feature-parity-tauri-tui-gaps.md`) tasks complete, so there is a proven, spec-conformant
multi-language base to port *from*; and (2) the maintainer green-lighting this initiative and providing
the mobile prerequisites that are outside the agent's control — an **Apple Developer account + a Mac with
Xcode** (iOS/iPadOS) and the **Android SDK/NDK + a device or emulator** (none are in the sandbox today).
**Recheck:** `ls tasks/ | grep -E 'cpp-add-wx|rust-feature-parity'` — when both parity tasks have moved to
`tasks/archive/`, the foundation half is clear; the hardware/account half and the go-ahead are the
maintainer's to signal.
**Priority:** 8 (blocked) **Difficulty:** 9
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: "when [the parity work is]
done, I'm going to want to add an Android port, an iPhone port, an iPad port, a golang HTML server based
implementation. And when those are all complete … extract what we've learned about product development
using these reference documents to make multiple implementations across languages from desktop, to web,
to mobile, into runClaudeInContainer and runCrushInContainer. I'm going to want to research what code
could be shared across mobile and desktop and web — I assume C or C++ or rust would be common for the
engine. But do some research now, and write up a task."

## BLUF

Two phases, after the desktop/web parity foundation lands. **Phase 1 — platform ports:** add an
**Android** app, an **iPhone** app, an **iPad** app, and a **Go HTTP server** that serves hanoi as an
HTML UI. Each conforms to the UI-independent **feature spec** (`tasks/reference/feature-spec.md`, the
parity authority) exactly as the desktop/web front-ends do. **Phase 2 — harvest the methodology:** once
all ports exist, extract the durable product-development lessons (a UI-independent spec → a shared core →
thin platform-native UIs; what code is sharable across desktop/web/mobile and how it's bound to each
platform) into **shared reference docs in `runClaudeInContainer` + `runCrushInContainer`** (`tasks/
reference/`, mirrored byte-identically, like the other cross-project conventions), so the recipe is
reusable for any future multi-platform product. "Done" = the four ports exist and pass the spec §7
checklist, and the methodology reference doc is written + mirrored into both sandboxes.

## Context (read first)

- **The enabler is already built:** `tasks/reference/feature-spec.md` defines the program
  UI-independently + gives a per-implementation compliance checklist (§7). Every port is checked against
  it — the spec is the contract that makes "N implementations of one product" tractable. The audit that
  produced it: `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- **Candidate shared cores already exist in-repo:** the **Rust `hanoigame` crate** (`rust/hanoigame/`)
  and the **header-only C++ engine** (`cpp/src/{model,presenter,recipe}.hpp`). Either can be the
  cross-platform core; the Python package stays the behaviour oracle. hanoi already proves the
  **shared-core → thin-front-end** split *within* a language — this initiative extends it *across the
  FFI boundary* to mobile/web.
- **This is a big, maintainer-driven initiative** (new SDKs, app-store toolchains, devices, accounts) —
  hence blocked, not merely sequenced. When unblocked, split Phase 1 into one step-task per port (Android
  / iOS-iPhone / iPadOS / Go-web) under this umbrella, each archiving on its own completion.

## Research — what code is sharable across mobile / desktop / web (2026-10-25)

The settled industry pattern is **one shared core (the engine) written in a systems language, with a
thin platform-native UI on top** — exactly the maintainer's assumption (C/C++ or Rust for the engine).
What differs per platform is only *how the core is bound to the UI*:

### Option A — Rust core (recommended if we pick one)
- **The core:** keep the game logic in the `rust/hanoigame` crate (already spec-complete per the audit).
- **Android:** build the crate to a `.so` with **cargo-ndk**; expose it to Kotlin via **UniFFI**
  (Mozilla) or JNI; UI in Jetpack Compose.
- **iPhone + iPad:** build a static lib for the Apple targets; **UniFFI generates Swift bindings**; UI in
  SwiftUI (one codebase adapts to iPhone/iPad size classes — the iPad "port" is largely layout, not a
  separate engine). Needs a Mac + Xcode + Apple Developer account.
- **Web:** compile the crate to **wasm** (wasm-bindgen / Trunk) — hanoi already has the egui-web and
  Tauri paths as precedent.
- **Desktop:** native (already done — CLI/TUI/wx/Tauri).
- **Why Rust:** **UniFFI** generates type-safe Swift/Kotlin (and Python/JS) bindings from one Rust core,
  so the engine is written once and each platform gets native calls. Caveat to plan for: UniFFI's
  JNA-based loading skips `JNI_OnLoad` on Android (crates needing an Android context can trip on it) —
  an init bridge is the known workaround.

### Option B — C++ core
- **The core:** the header-only `cpp/src/*.hpp` engine (portable C++17).
- **Android:** NDK (JNI) builds the engine as a `.so`; UI in Kotlin/Compose.
- **iPhone + iPad:** C++ compiles directly for Apple targets and bridges to Swift via **Objective-C++**;
  UI in SwiftUI.
- **Web:** **Emscripten** → wasm (hanoi already does this for the ImGui GUI).
- **Desktop:** native (ImGui, done).
- **Caveat:** Microsoft's Visual Studio 2026 is retiring its iOS/Android C++ *workload* (the NDK itself
  stays supported) — so drive the mobile builds from the NDK + Xcode directly, not that workload.

### The Go web server (a distinct shape)
Go doesn't share a Rust/C++ core cleanly without cgo/FFI. The simplest, spec-driven path: **a pure-Go
reimplementation of the engine** (another port conforming to `feature-spec.md`) behind a `net/http`
server that serves the HTML UI (server-rendered + HTMX, or a small JS client; board + the three-panel
rebinding view as HTML). This is where the spec pays off most — a clean-room Go port is a checklist
exercise, not reverse-engineering. (Embedding the Rust/C++ core via cgo is possible but couples the Go
build to the FFI core; prefer the independent Go port unless there's a reason to share.)

### The product-development lesson to harvest (Phase 2)
The reusable recipe across all of this: **(1)** write a UI-independent **feature spec** + a compliance
checklist (done here); **(2)** keep one **shared core** in a systems language (Rust via UniFFI/wasm, or
C++ via NDK/Emscripten/Obj-C++); **(3)** write **thin platform-native UIs** (SwiftUI, Jetpack Compose,
HTML/DOM, desktop toolkits) that each satisfy the spec; **(4)** where a platform can't share the core
(Go), a spec-conformant reimplementation is cheap *because* the spec exists. That is the content Phase 2
extracts into the sandboxes.

## Plan

**Phase 1 — ports (each a step-task when unblocked, each spec §7-checked):**
1. Decide the shared-core language (Rust vs C++ — open question 1) and stand up the binding toolchain.
2. **Android** app (shared core + Compose UI).
3. **iPhone** app (shared core via UniFFI/Obj-C++ + SwiftUI).
4. **iPad** app (same core; iPad layout — likely a size-class variant of the iPhone SwiftUI app, not a
   separate engine).
5. **Go HTTP server** serving the HTML UI (pure-Go spec-conformant engine + `net/http`).

**Phase 2 — methodology harvest (after all four ports exist):**
6. Write a shared reference doc — "building one product across desktop/web/mobile in several languages" —
   into `runClaudeInContainer tasks/reference/` and mirror it byte-identically into
   `runCrushInContainer tasks/reference/` (the convention for shared cross-project docs). Cite hanoi as
   the worked example; cover the spec→core→thin-UI recipe, the per-platform binding tools, and what is /
   isn't sharable. Consider also a capsule in the personal overlay's project-template guidance.

## Open questions

1. **Shared-core language — Rust or C++?** (Recommend **Rust**: UniFFI gives one core → Swift + Kotlin +
   wasm bindings with the least glue; the crate is already spec-complete. C++ is viable via NDK/Emscripten/
   Obj-C++ and the header-only engine, but needs more per-platform binding code.)
2. **Go: reimplement the engine in Go, or share the core via cgo?** (Recommend a **pure-Go reimplementation**
   conforming to the spec — a server shouldn't drag an FFI core into its build.)
3. **iPad: a separate port or a size-class variant of the iPhone app?** (Recommend variant — same core +
   SwiftUI adapting to the iPad idiom, unless the maintainer wants a distinct iPad UX.)
4. **Scope of the Phase-2 harvest** — a single methodology reference doc (recommended), or a layered set
   if it grows?

## Related

- The contract: `tasks/reference/feature-spec.md`; the audit: `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- The foundation this is blocked on: `tasks/cpp-add-wx-frontend-and-recipe-view-parity.md`,
  `tasks/rust-feature-parity-tauri-tui-gaps.md`.
- Candidate cores: `rust/hanoigame/`, `cpp/src/{model,presenter,recipe}.hpp`.
- Research sources (2026-10-25): cross-platform C++ (NDK/Emscripten/iOS) —
  https://levelup.gitconnected.com/cross-platform-mobile-and-web-development-with-c-explained-aac9952b4f8c
  and Microsoft's VS C++ mobile docs
  https://learn.microsoft.com/en-us/cpp/cross-platform/visual-cpp-for-cross-platform-mobile-development ;
  Rust shared-core + UniFFI bindings (Swift/Kotlin/JS, the Android `JNI_OnLoad` caveat) — the `jffi`
  crate docs, https://docs.rs/crate/jffi/0.4.16 .
