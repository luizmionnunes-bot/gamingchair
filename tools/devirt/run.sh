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
# 0b. VM native table t[15] (consumed as __NATIVE by emit.py/final.py)
python3 "$T/natives.py" "$W/run.lua" "$W/natives.lua"
# 1. decoded VM bytecode -> bytecode.bin (phase 1: drops the dependency on t[18])
cat "$T/base.lua" "$T/bcdump.lua" > "$W/pre_bc.lua"
python3 "$T/hook.py" "$W/harness.lua" "$W/h_bc.lua" "$W/pre_bc.lua"
timeout 300 "$L/luau" "$W/h_bc.lua" 2>/dev/null > "$W/bc.out" || true
python3 - "$W" <<'PY'
import sys
w = sys.argv[1]
s = open(w + '/bc.out', 'rb').read().decode('latin1')
i = s.index('BEGINBC '); n = int(s[i + 8:s.index('\n', i)])
body = s[s.index('\n', i) + 1:s.index('ENDBC')].replace('\n', '')
b = bytes.fromhex(body)
assert len(b) == n, (len(b), n)
open(w + '/bytecode.bin', 'wb').write(b)
print('bytecode.bin', n, 'bytes')
PY

# 2. proto tree dump (reconstructed holes plugged in)
cat "$T/base.lua" "$T/reconstructed.lua" "$T/dumper.lua" > "$W/pre_dump.lua"
python3 "$T/hook.py" "$W/harness.lua" "$W/h_dump.lua" "$W/pre_dump.lua"
timeout 300 "$L/luau" "$W/h_dump.lua" 2>/dev/null > "$W/dump.out" || true
python3 - "$W" <<'PY'
import sys
w=sys.argv[1]; s=open(w+'/dump.out','rb').read().decode('latin1')
a=s.index('BEGINDUMP\n')+10; b=s.index('\nENDDUMP')
open(w+'/proto.json','w').write(s[a:b].replace('\n',''))
PY
# 3. runtime constants t[1] after VM init
cat "$T/base.lua" "$T/reconstructed.lua" "$T/dumpt1.lua" > "$W/pre_t1.lua"
echo 'function HOOK_POST(p,t) DUMPT1(t) error("stop") end' >> "$W/pre_t1.lua"
python3 "$T/hook.py" "$W/harness.lua" "$W/h_t1.lua" "$W/pre_t1.lua"
timeout 120 "$L/luau" "$W/h_t1.lua" 2>&1 | grep -a "^T1 \|^TN " > "$W/t1post.txt" || true
# 4. linearized source + opcode handler map
python3 "$T/flat.py" "$R/gamingchairac.deob.lua" --ast "$W/deob.json" --out "$W/deob.flat.lua"
python3 "$T/opmap.py" "$R/gamingchairac.deob.lua" "$W/deob.json" "$W/t1post.txt" "$W/ops.txt" --json "$W/ops.json"
# 5. deliverables: the bytecode listing and the devirtualized program
python3 "$T/dumpprotos.py" "$W" "$R/gamingchairac.protos.txt"
python3 "$T/emitsrc.py" "$W" "$R/gamingchairac.src.lua"
echo "done: $W"
