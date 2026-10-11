#!/bin/sh
# Reproduce the static devirtualization pipeline.
#   tools/devirt/run.sh <luau-bin-dir> <work-dir>
# Needs the Luau release binaries (luau, luau-ast, luau-compile):
#   https://github.com/luau-lang/luau/releases (luau-ubuntu.zip)
# The script is only *executed in an isolated Luau VM* (no network, no Roblox)
# to obtain data the VM computes from constants: the decoded bytecode and the
# deserialized prototype tree. Nothing interacts with a game.
set -e
L=${1:?luau bin dir}; W=${2:?work dir}
R=$(cd "$(dirname "$0")/../.." && pwd); T=$R/tools/devirt
mkdir -p "$W"
export LUAU_AST=$L/luau-ast
# 0. runnable copy + harness (stdlib decoder hooks)
cp "$R/gamingchairac.deob.lua" "$W/run.lua"
python3 "$R/tools/make_runnable.py" "$W/run.lua" "$L/luau-compile"
python3 "$R/tools/mkharness.py" "$W/run.lua" "$W/harness.lua"
# 1. proto tree dump (reconstructed holes plugged in)
cat "$T/base.lua" "$T/reconstructed.lua" "$T/dumper.lua" > "$W/pre_dump.lua"
python3 "$T/hook.py" "$W/harness.lua" "$W/h_dump.lua" "$W/pre_dump.lua"
timeout 300 "$L/luau" "$W/h_dump.lua" 2>/dev/null > "$W/dump.out" || true
python3 - "$W" <<'PY'
import sys
w=sys.argv[1]; s=open(w+'/dump.out','rb').read().decode('latin1')
a=s.index('BEGINDUMP\n')+10; b=s.index('\nENDDUMP')
open(w+'/proto.json','w').write(s[a:b].replace('\n',''))
PY
# 2. runtime constants t[1] after VM init
cat "$T/base.lua" "$T/reconstructed.lua" "$T/dumpt1.lua" > "$W/pre_t1.lua"
echo 'function HOOK_POST(p,t) DUMPT1(t) error("stop") end' >> "$W/pre_t1.lua"
python3 "$T/hook.py" "$W/harness.lua" "$W/h_t1.lua" "$W/pre_t1.lua"
timeout 120 "$L/luau" "$W/h_t1.lua" 2>&1 | grep -a "^T1 \|^TN " > "$W/t1post.txt" || true
# 3. linearized source + opcode handler map
python3 "$T/flat.py" "$R/gamingchairac.deob.lua" --ast "$W/deob.json" --out "$W/deob.flat.lua"
python3 "$T/opmap.py" "$R/gamingchairac.deob.lua" "$W/deob.json" "$W/t1post.txt" "$W/ops.txt" --json "$W/ops.json"
echo "done: $W"
