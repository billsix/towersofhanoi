# Fixed the C++ build: `item_id` was used but no longer declared in `cpp/hanoiwx.cpp`

**Done 2026-11-27** (agent; William Emerison Six <billsix@gmail.com>, 2026-11-27: "take a look at hanoi, checks / cpp-build (push) Failing after 1m. take a look at the git history to see what caused it to fail, make a task to fix it", then "go ahead and fix it now").

## The failure

The `checks / cpp-build` job (`make build USE_EMACS=0 USE_WASM=0` in `cpp/`) stopped on one compile error in the wxWidgets front-end:

```
/hanoi-cpp/hanoiwx.cpp: In member function 'void {anonymous}::HanoiFrame::build_menu_bar()':
/hanoi-cpp/hanoiwx.cpp:526:11: error: 'item_id' was not declared in this scope
```

## What caused it (from the git history)

- Commit `8e2f866` ("Apply the naming and scope rules to the GUI code and the front-end locals", 2026-11-25) replaced, in the loop over `kRelabelPerms`,

  ```cpp
  const int item_id = wxXmlResource::GetXRCID(id);
  wxMenuItem *item = mb->FindItem(item_id);
  ```

  with `wxMenuItem *item = mb->FindItem(wxXmlResource::GetXRCID(id));`. The `Bind(wxEVT_MENU, …, item_id);` a few lines below still named `item_id`.
- `item_id` had two uses, so the rule that commit was applying ("inline a binding used once") never covered it.
- The workflow's runs on GitHub (public API, read 2026-11-27): the last green run was `d0155b5` (2026-11-25); the first red one was `05cf602`, the merge that brought `8e2f866` in (2026-11-26); every run after it was red, each with only `cpp-build` failing. `cpp-test` stayed green because it builds only the `hanoi-tests` target.

## The fix

The local is back: `const int item_id = wxXmlResource::GetXRCID(id);`, passed to both `FindItem` and `Bind`. Nothing else changed.

## Verified (2026-11-27, in the existing `hanoi-cpp` image, with the CI jobs' own commands)

- Before the fix, a keep-going build (`cmake --build … -- -k 0`) reported this one error and no other; the ImGui app and `hanoi-tests` built. So none of the other names `8e2f866` inlined in `cpp/hanoiwx.cpp` and `cpp/main.cpp` was left behind.
- After it: `cmake -S . -B build -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON && cmake --build build` exit 0, `hanoi-wx` linked; `ctest` 100% passed; `/format.sh` (clang-format) changed no file; `tools/check-no-network.sh` exit 0.
- `hanoi-wx` was run on a virtual display (Xvfb, `GDK_BACKEND=x11`) and driven with `xdotool`, with a screenshot of each step read: it started, the three-disc game was solved by keyboard in 7 moves (relabelling unlocks after the first win), the "Relabel pegs" menu opened with its six entries, and choosing "1 3 2" relabelled the board (status line: "Relabelled: physical pegs 1,2,3 now show as 1,3,2."). That menu entry is bound by the line that had been broken.

## A false claim in an archived record

`tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language.md` says of the pass that made the change: "`hanoi-cpp` image: `cmake --build build` built all three programs; `ctest` 100% passed", and that the C++ wx GUI was run on a virtual display. The committed `hanoiwx.cpp` did not compile, so it cannot have been what was built. How that happened was not established; a build made before the file's last edit would explain it. The archived record is left as written, and this one is the correction.

## Not done

GitHub's run is green only after the maintainer commits and pushes; `checks / cpp-build` on that push is the last confirmation.
