# Fix the C++ build: `item_id` is used but no longer declared in `cpp/hanoiwx.cpp`

**Status:** proposed — needs go-ahead
**Priority:** 2 (the `checks / cpp-build` job has failed on every push since 2026-11-26)
**Difficulty:** 1
**Created:** 2026-11-27 (William Emerison Six <billsix@gmail.com>: "take a look at hanoi, checks / cpp-build (push) Failing after 1m. take a look at the git history to see what caused it to fail, make a task to fix it")

## BLUF

The wxWidgets front-end `cpp/hanoiwx.cpp` does not compile: commit `8e2f866` inlined the local `item_id` into one of its two uses and left the other. Done means the `cpp-build` job's own command (`make build USE_EMACS=0 USE_WASM=0` in `cpp/`) exits 0 and the next push shows `checks / cpp-build` green.

## Context

**Read first:** `cpp/hanoiwx.cpp`, the loop over `kRelabelPerms` in `HanoiFrame::build_menu_bar`; `cpp/Makefile`, target `build`; `.github/workflows/checks.yml`, job `cpp-build`.

### The error

```
/hanoi-cpp/hanoiwx.cpp: In member function 'void {anonymous}::HanoiFrame::build_menu_bar()':
/hanoi-cpp/hanoiwx.cpp:526:11: error: 'item_id' was not declared in this scope
  526 |           item_id);
```

Reproduced on 2026-11-27 in the existing `hanoi-cpp` image with the job's cmake commands, building into a throwaway directory. With ninja told to keep going (`-- -k 0`) this is the only error: the ImGui app and `hanoi-tests` build.

### What caused it (from the git history)

- Commit `8e2f866` ("Apply the naming and scope rules to the GUI code and the front-end locals", 2026-11-25) replaced

  ```cpp
  const int item_id = wxXmlResource::GetXRCID(id);
  wxMenuItem *item = mb->FindItem(item_id);
  ```

  with `wxMenuItem *item = mb->FindItem(wxXmlResource::GetXRCID(id));`. The `Bind(wxEVT_MENU, …, item_id);` four lines below still names `item_id`.
- `item_id` had **two** uses, so the rule the commit was applying ("inline a binding used once") never covered it.
- The workflow runs on GitHub (public API, read 2026-11-27): the last green run is `d0155b5` (2026-11-25); the first red one is `05cf602`, the merge that brought `8e2f866` in (2026-11-26); every run since is red, each with only the `cpp-build` job failing. `cpp-test` stays green because it builds only the `hanoi-tests` target.

### A false claim in an archived record

`tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language.md` says of that pass: "`hanoi-cpp` image: `cmake --build build` built all three programs; `ctest` 100% passed", and that the C++ wx GUI was run on a virtual display. The committed `hanoiwx.cpp` cannot have been what was built: it does not compile. The likely sequence is that the build ran before the last edit to the file, but that was not established. The archived record is left as written; this task is the correction.

## Plan

1. In `build_menu_bar`, restore the local: `const int item_id = wxXmlResource::GetXRCID(id);`, pass it to both `FindItem` and `Bind`. It is read twice, so it keeps its name.
2. Run the job's own command from `cpp/`: `make build USE_EMACS=0 USE_WASM=0` (nested: if `: image` starts a full rebuild, run the target's `podman run` line against the existing `hanoi-cpp` image instead). It must exit 0.
3. `make check-format USE_EMACS=0 USE_WASM=0 USE_WX=0` and `make test USE_EMACS=0 USE_WASM=0`, the other two C++ jobs.
4. Re-read the other inlinings `8e2f866` made in `cpp/hanoiwx.cpp` and `cpp/main.cpp` (the archived record lists them) for a second leftover name. The keep-going build found none, so this is a read, not an expected fix.
5. Start `make wx` once under Xvfb and open the Relabel menu, since the broken line is the one that binds those menu items.
6. After the maintainer pushes, confirm `checks / cpp-build` is green.

## Open questions

None.
