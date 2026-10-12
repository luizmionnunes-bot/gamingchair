# Deobfuscation pipeline tools

Transforms `gamingchairac.unflat.lua` (Stage A output) toward readable source.

- `sm.py`   — state-machine CFG extractor (luau-ast JSON based); inventory + Stage C engine.
- `stageB.py` — Stage B: scope-aware dead-code removal (AST liveness).
- `stageR.py` — Stage R: rename f1's constant-pool params to stdlib names.
- `stageC.py`  — Stage C lowering: state machine -> basic-block CFG (effects vs routing).
- `stageC2.py` — Stage C structuring: acyclic -> native if/else, verified by symbolic
  traces + effect-coverage, then spliced into the handler.

Validation uses the Luau tools (`luau-ast`, `luau-compile`) from
https://github.com/luau-lang/luau/releases (`luau-ubuntu.zip`), not committed here.
Each stage is validated by `luau-ast` (exit 0 = valid syntax) and checked for
state-graph preservation via `sm.py`.

## Static string resolution (Stage D)
- `luaeval.py`    — Lua(u)-subset tree-walking interpreter over luau-ast JSON.
- `stdlib_lua.py` — Luau standard runtime in Python (string/table/math/coroutine/
  buffer/bit32/task/os + builtins); task.* are no-ops so the VM never starts.
- `decode2.py`    — runs f1's init in the interpreter, stops at t[19]=t[18](blob),
  recovering the 189KB VM bytecode statically; embedded length-prefixed string
  constants are then scanned out into ../gamingchairac.strings.txt.
- `mkharness.py` / `make_runnable.py` — earlier Luau-based emulation harness (not
  used for the final static result; kept for reference).
