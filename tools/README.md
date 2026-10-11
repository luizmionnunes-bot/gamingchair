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
