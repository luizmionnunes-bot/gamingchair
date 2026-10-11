#!/usr/bin/env python3
"""Add instrumentation hooks to a harness built by tools/mkharness.py.
usage: hook.py harness.lua out.lua prelude.lua
- Appends `HOOK_<name>(...)` after the VM pipeline assignments
  (t[19]=t[18](blob), t[120]=t[114](t[19]), t[121]=t[116](t[120])).
- Replaces every decompiler hole `-- structuring failed for function N`
  with a call to HOOK_STUB[N](<params>) (error "STUB N" if not provided),
  so reconstructed bodies can be plugged in from the prelude.
The prelude (Lua) defines HOOK_* and HOOK_STUB."""
import sys, re
src, dst, pre = sys.argv[1:4]
prelude = open(pre).read()
L = open(src, encoding='utf-8', errors='surrogateescape').read().split('\n')
def after(pat, code, count=1):
    n = 0
    for i, l in enumerate(L):
        if re.search(pat, l):
            L[i] = l + ' ' + code; n += 1
    assert n == count, (pat, n)
after(r't\[19\] = t\[18\]\(', 'HOOK_BC(t[19], t)')
after(r't\[120\] = t\[114\]\(t\[19\]\)', 'HOOK_PROTO(t[120], t)')
after(r't\[121\] = t\[116\]\(t\[120\]\)', 'HOOK_POST(t[121], t)')
after(r'^\s*local v17 = v16\[v14\]$', 'if HOOK_INS then HOOK_INS(v1, sum_2, v16, v17, v72, sum_3) end')
for i, l in enumerate(L):
    m = re.search(r'-- structuring failed for function (\d+);', l)
    if not m: continue
    n = m.group(1)
    sig = re.search(r'function\s*\(([^)]*)\)\s*--\[\[ Line: \d+(?: \| Upvalues: ([^\]]*))?', L[i-1])
    params = sig.group(1).strip() if sig else ''
    args = params if params else ''
    ups = sig.group(2) if sig and sig.group(2) else ''
    upn = [u.split(' ')[0] for u in ups.split(', ') if u]
    upt = '{' + ', '.join(f'{u}=function() return {u} end' for u in upn if u != '...') + '}'
    L[i] = l[:m.start()] + f'do local h = HOOK_STUB[{n}] if not h then error("STUB {n}") end return h({upt}{", " if args else ""}{args}) end'
s = '\n'.join(L)
i = s.index('local function f1(')
s = s[:i] + prelude + '\n' + s[i:]
open(dst, 'w', encoding='utf-8', errors='surrogateescape').write(s)
